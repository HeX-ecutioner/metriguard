import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.db.crud import (
    create_inspection,
    get_inspection,
    add_package_image,
    add_declaration,
    add_violation,
    set_inspection_result,
    update_inspection_status,
)
from app.db.models import InspectionStatus
from app.services.ai_extractor import extract_information
from app.services.rule_engine import evaluate_compliance
from app.models.schemas import (
    InspectionCreateRequest,
    InspectionDetailResponse,
    PackageImageResponse,
)
from app.services.image_validator import validate_and_decode_image, ImageValidationError
from app.services.storage import get_storage_service, StorageError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Inspections"])


@router.post(
    "/inspections",
    response_model=InspectionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inspection session"
)
def create_inspection_session(
    payload: Optional[InspectionCreateRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Creates a new commodity inspection session in the database.
    """
    product_name = payload.product_name if payload else None
    notes = payload.notes if payload else None

    inspection = create_inspection(
        db=db,
        product_name=product_name,
        notes=notes
    )
    return inspection


@router.post(
    "/inspections/{inspection_id}/images",
    response_model=PackageImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and validate a commodity package image"
)
async def upload_inspection_image(
    inspection_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads an image to an existing inspection session:
    - Validates MIME type, extension, size, image decoding, and dimensions
    - Securely stores the file in local storage with generated UUID filename
    - Saves image metadata in SQLite (without storing raw binary data in DB)
    """
    # 1. Verify inspection exists
    inspection = get_inspection(db=db, inspection_id=inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with ID {inspection_id} not found."
        )

    # 2. Read file bytes
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(e)}"
        )

    original_filename = file.filename or "uploaded_package.jpg"
    content_type = file.content_type or ""

    # 3. Validate image
    try:
        validated = validate_and_decode_image(
            content=content,
            original_filename=original_filename,
            content_type=content_type,
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB
        )
    except ImageValidationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )

    # 4. Save file to storage
    storage = get_storage_service()
    try:
        # Pass sanitized basename to storage service
        safe_original = Path(original_filename).name
        file_key = await storage.save_file(filename=safe_original, content=content)
    except StorageError as se:
        logger.error(f"Storage failure for inspection {inspection_id}: {se.detail}")
        raise HTTPException(
            status_code=se.status_code,
            detail=se.detail
        )

    # 5. Persist image metadata into database
    try:
        package_image = add_package_image(
            db=db,
            inspection_id=inspection_id,
            file_path=file_key,
            original_filename=safe_original,
            mime_type=validated.mime_type,
            file_size=validated.file_size,
            width=validated.width,
            height=validated.height
        )
    except Exception as db_err:
        logger.error(f"Failed to record image metadata in database: {db_err}")
        # Clean up stored file if database insertion fails
        await storage.delete_file(file_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record image metadata in database."
        )

    # 6. AI text extraction (OCR with lightweight/Paddle/mock fallback)
    try:
        extracted_data = extract_information(content)
    except Exception as e:
        logger.error(f"Error during AI extraction for image {package_image.id}: {e}")
        extracted_data = []

    # 7. Evaluate Legal Metrology compliance
    try:
        compliance_result = evaluate_compliance(extracted_data)
    except Exception as e:
        logger.error(f"Error during compliance evaluation for image {package_image.id}: {e}")
        compliance_result = None

    # 8. Persist Declarations, Violations, Result, and Update Inspection Status
    if compliance_result:
        try:
            for item in extracted_data:
                add_declaration(
                    db=db,
                    inspection_id=inspection_id,
                    declaration_type="extracted_text",
                    extracted_value=item.get("text", "") if isinstance(item, dict) else str(item),
                    confidence=item.get("confidence") if isinstance(item, dict) else None,
                    source_image_id=package_image.id,
                    bounding_box=item.get("box") if isinstance(item, dict) else None,
                )

            for v in compliance_result.violations:
                add_violation(
                    db=db,
                    inspection_id=inspection_id,
                    rule_id=v.rule_id,
                    title=v.rule_id,
                    explanation=v.explanation,
                    confidence=v.confidence,
                    evidence_image_id=package_image.id,
                )

            try:
                status_enum = InspectionStatus(compliance_result.status)
            except ValueError:
                status_enum = InspectionStatus.MANUAL_REVIEW

            set_inspection_result(
                db=db,
                inspection_id=inspection_id,
                final_status=status_enum,
                summary=f"Inspection completed with status {status_enum.value}. Detected {len(compliance_result.violations)} violations."
            )
            update_inspection_status(
                db=db,
                inspection_id=inspection_id,
                status=status_enum,
                overall_confidence=compliance_result.confidence_score
            )
        except Exception as persist_err:
            logger.warning(f"Failed to persist compliance outcome to database: {persist_err}")

    return PackageImageResponse(
        id=package_image.id,
        inspection_id=package_image.inspection_id,
        file_path=package_image.file_path,
        original_filename=package_image.original_filename,
        mime_type=package_image.mime_type,
        file_size=package_image.file_size,
        width=package_image.width,
        height=package_image.height,
        created_at=package_image.created_at,
        status=compliance_result.status if compliance_result else None,
        confidence_score=compliance_result.confidence_score if compliance_result else None,
        extracted_texts=compliance_result.extracted_texts if compliance_result else None,
        violations=compliance_result.violations if compliance_result else None,
    )


@router.get(
    "/inspections/{inspection_id}",
    response_model=InspectionDetailResponse,
    summary="Retrieve an inspection session and attached images"
)
def get_inspection_details(
    inspection_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves an inspection session along with all uploaded images and current status.
    """
    inspection = get_inspection(db=db, inspection_id=inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with ID {inspection_id} not found."
        )
    return inspection
