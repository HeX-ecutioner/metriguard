"""
FastAPI Router for MetriGuard Package Declaration Extraction.
Exposes extraction endpoints decoupled from legal compliance evaluation.
Supports deterministic parsing, ambiguity identification, and multi-candidate tracking.
"""

import logging
from typing import Optional, List, Union, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.crud import get_inspection, add_declaration
from app.models.ocr_schemas import OCRResult, OCRItem
from app.models.declaration_schemas import (
    DeclarationExtractionResult,
    ExtractionStatus,
)
from app.services.extraction import (
    DeclarationExtractor,
    extract_declarations,
    DEFAULT_CONFIDENCE_THRESHOLD,
)
from app.services.ocr.service import OCRService, get_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extract", tags=["Declaration Extraction"])


class DirectExtractionRequest(BaseModel):
    """Payload for direct declaration extraction from raw OCR text or items."""
    text: Optional[str] = Field(None, description="Consolidated raw OCR text (multiline)")
    items: Optional[List[OCRItem]] = Field(None, description="List of OCR items with coordinates and confidences")
    image_id: Optional[Union[int, str]] = Field(None, description="Optional image identifier for traceability")
    confidence_threshold: Optional[float] = Field(
        DEFAULT_CONFIDENCE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for marking FOUND vs LOW_CONFIDENCE"
    )


@router.post(
    "/declarations",
    response_model=DeclarationExtractionResult,
    summary="Extract declarations from raw OCR text or OCR items"
)
def extract_declarations_from_text(payload: DirectExtractionRequest):
    """
    Deterministic declaration extraction from OCR text or items:
    - Extracts all 13 Legal Metrology declaration types
    - Preserves OCR line evidence, bounding boxes, and confidences
    - Detects conflicts and flags AMBIGUOUS declarations for manual review
    - Pure extraction: DOES NOT perform legal compliance determinations
    """
    threshold = payload.confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD

    if payload.items:
        return extract_declarations(
            ocr_input=payload.items,
            image_id=payload.image_id,
            confidence_threshold=threshold
        )
    elif payload.text:
        return extract_declarations(
            ocr_input=payload.text,
            image_id=payload.image_id,
            confidence_threshold=threshold
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'items' or 'text' must be provided for declaration extraction."
        )


@router.post(
    "/ocr-result",
    response_model=DeclarationExtractionResult,
    summary="Extract declarations directly from standardized OCRResult"
)
def extract_declarations_from_ocr_result(
    ocr_result: OCRResult,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
):
    """
    Direct extraction pipeline accepting a full OCRResult:
    - Parses recognized items and envelope bounding box
    - Resolves candidates across 13 declaration types
    - Marks ambiguous or low-confidence values
    - Completely separate from compliance rule evaluation
    """
    return extract_declarations(
        ocr_input=ocr_result,
        image_id=ocr_result.image_id,
        confidence_threshold=confidence_threshold
    )


@router.post(
    "/inspections/{inspection_id}",
    response_model=DeclarationExtractionResult,
    summary="Run OCR extraction and persist declarations for an inspection session"
)
def extract_and_store_inspection_declarations(
    inspection_id: int,
    image_id: Optional[int] = None,
    db: Session = Depends(get_db),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    Runs OCR and declaration extraction for an inspection session:
    - Processes inspection package images
    - Extracts 13 declaration types
    - Saves authoritative and candidate values to SQLite declarations table
    - DOES NOT compute compliance pass/fail or generate violations
    """
    inspection = get_inspection(db=db, inspection_id=inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session #{inspection_id} not found."
        )

    if not inspection.images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inspection #{inspection_id} has no uploaded images to extract declarations from."
        )

    # Select target image or use first image
    target_image = None
    if image_id is not None:
        target_image = next((img for img in inspection.images if img.id == image_id), None)
        if not target_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image #{image_id} not found under inspection #{inspection_id}."
            )
    else:
        target_image = inspection.images[0]

    # Run OCR via OCRService
    ocr_res = ocr_service.process_image(
        image_input=target_image.file_path,
        image_id=target_image.id,
        inspection_id=inspection_id,
        db=db
    )

    # Run declaration extractor
    extraction_result = extract_declarations(
        ocr_input=ocr_res,
        image_id=target_image.id
    )

    # Persist extracted declarations into database
    for decl_type, decl in extraction_result.declarations.items():
        if decl.status in (ExtractionStatus.FOUND, ExtractionStatus.LOW_CONFIDENCE):
            bbox_dict = decl.bounding_box.model_dump() if decl.bounding_box else None
            source_img_id = target_image.id if isinstance(target_image.id, int) else None
            add_declaration(
                db=db,
                inspection_id=inspection_id,
                declaration_type=decl_type.value,
                extracted_value=decl.value or "",
                confidence=decl.confidence,
                source_image_id=source_img_id,
                bounding_box=bbox_dict,
            )

    return extraction_result
