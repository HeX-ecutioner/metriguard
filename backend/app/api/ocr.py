"""
FastAPI Router for MetriGuard OCR Subsystem.
Exposes OCR processing endpoints decoupled from legal compliance evaluation.
"""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.crud import get_inspection
from app.models.ocr_schemas import (
    OCRResult,
    OCRError,
    UnreadableImageError,
    UnsupportedImageFormatError,
    ImageNotFoundError,
    OCRTimeoutError,
    OCRProviderError,
)
from app.services.ocr.service import OCRService, get_ocr_service
from app.services.image_validator import validate_and_decode_image, ImageValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR Processing"])


@router.post(
    "/process",
    response_model=OCRResult,
    summary="Process raw package image through OCR pipeline"
)
async def process_image_ocr(
    file: UploadFile = File(...),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    Direct OCR processing endpoint:
    - Loads and validates image bytes
    - Executes OpenCV preprocessing (resize, grayscale, CLAHE contrast, bilateral denoise)
    - Performs OCR text detection and recognition via provider abstraction
    - Normalizes results into OCRResult with bounding boxes and audit metadata
    - Completely separate from legal metrology compliance rules
    """
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded image file: {str(e)}"
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file provided."
        )

    filename = file.filename or "package.jpg"
    content_type = file.content_type or "image/jpeg"

    # Quick validation
    try:
        validate_and_decode_image(content, original_filename=filename, content_type=content_type)
    except ImageValidationError as ve:
        raise HTTPException(status_code=ve.status_code, detail=ve.detail)

    try:
        result = ocr_service.process_image(
            image_input=content,
            image_id=filename,
        )
        return result
    except UnreadableImageError as ue:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ue.detail)
    except UnsupportedImageFormatError as ufe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ufe.detail)
    except OCRTimeoutError as te:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=te.detail)
    except OCRProviderError as pe:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=pe.detail)
    except OCRError as oe:
        raise HTTPException(status_code=oe.status_code, detail=oe.detail)


@router.post(
    "/inspections/{inspection_id}/images/{image_id}",
    response_model=OCRResult,
    summary="Execute OCR on a stored inspection package image"
)
def process_inspection_image_ocr(
    inspection_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    Executes OCR pipeline for an existing commodity inspection image:
    - Retrieves image metadata and storage key from SQLite
    - Executes 9-stage OCR pipeline
    - Persists detected text elements into SQLite `declarations` table
    - Returns standardized OCRResult
    - Does NOT compute legal compliance determinations
    """
    inspection = get_inspection(db=db, inspection_id=inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session #{inspection_id} not found."
        )

    # Locate package image within inspection
    target_image = next((img for img in inspection.images if img.id == image_id), None)
    if not target_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image #{image_id} not found under inspection #{inspection_id}."
        )

    try:
        result = ocr_service.process_image(
            image_input=target_image.file_path,
            image_id=target_image.id,
            inspection_id=inspection_id,
            db=db,
        )
        return result
    except ImageNotFoundError as infe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=infe.detail)
    except UnreadableImageError as ue:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ue.detail)
    except UnsupportedImageFormatError as ufe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ufe.detail)
    except OCRTimeoutError as te:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=te.detail)
    except OCRProviderError as pe:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=pe.detail)
    except OCRError as oe:
        raise HTTPException(status_code=oe.status_code, detail=oe.detail)
