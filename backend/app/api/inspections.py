import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.crud import (
    create_inspection,
    get_inspection,
    list_inspections,
)
from app.models.schemas import (
    InspectionCreateRequest,
    InspectionDetailResponse,
    PackageImageResponse,
)
from app.services.storage import get_storage_service
from app.services.inspection_orchestrator import (
    InspectionOrchestrator,
    get_inspection_orchestrator,
)

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


@router.get(
    "/inspections",
    response_model=List[InspectionDetailResponse],
    summary="List inspection sessions"
)
def list_inspection_sessions(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieves recent inspection sessions with optional status and text search filtering.
    """
    return list_inspections(db=db, skip=skip, limit=limit, status_filter=status, search=search)



@router.post(
    "/inspections/{inspection_id}/images",
    response_model=PackageImageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Inspection session already contains an uploaded image or has already been completed."
        }
    },
    summary="Upload and orchestrate Legal Metrology inspection for a package image"
)
async def upload_inspection_image(
    inspection_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    orchestrator: InspectionOrchestrator = Depends(get_inspection_orchestrator)
):
    """
    Uploads a package image to an inspection session and executes the full orchestrated pipeline:
    1. Validates image MIME, dimensions, and size.
    2. Stores the image securely.
    3. Executes OCR text recognition.
    4. Extracts structured Legal Metrology declarations.
    5. Runs deterministic regulatory rule evaluation.
    6. Persists findings, violations, and synthesized outcomes in SQLite.
    """
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

    return await orchestrator.process_image_upload(
        db=db,
        inspection_id=inspection_id,
        file_bytes=content,
        filename=original_filename,
        content_type=content_type,
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
    Retrieves an inspection session along with all uploaded images, declarations, violations, and results.
    """
    inspection = get_inspection(db=db, inspection_id=inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with ID {inspection_id} not found."
        )
    return inspection


@router.get(
    "/inspections/{inspection_id}/images/{image_id}/file",
    summary="Retrieve the original uploaded package image file"
)
async def get_inspection_image_file(
    inspection_id: int,
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Serves the original package image file for visual verification and audit evidence.
    """
    inspection = get_inspection(db=db, inspection_id=inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection with ID {inspection_id} not found."
        )

    target_image = next((img for img in inspection.images if img.id == image_id), None)
    if not target_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found in inspection {inspection_id}."
        )

    storage = get_storage_service()
    local_path = storage.get_file_path(target_image.file_path)
    if local_path and Path(local_path).exists():
        return FileResponse(
            path=str(local_path),
            media_type=target_image.mime_type,
            filename=target_image.original_filename
        )

    # Fallback to byte retrieval
    file_bytes = await storage.get_file(target_image.file_path)
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found in storage."
        )

    return Response(
        content=file_bytes,
        media_type=target_image.mime_type,
        headers={"Content-Disposition": f'inline; filename="{target_image.original_filename}"'}
    )
