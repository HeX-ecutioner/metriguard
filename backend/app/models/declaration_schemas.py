"""
Domain schemas for MetriGuard declaration extraction from OCR output.
Covers the 13 required declaration types, multi-candidate traceability,
and ambiguity resolution indicators.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from app.models.ocr_schemas import OCRBoundingBox


class DeclarationType(str, Enum):
    """The 13 supported packaged commodity declaration types."""
    COMMODITY_NAME = "COMMODITY_NAME"
    MANUFACTURER = "MANUFACTURER"
    PACKER = "PACKER"
    IMPORTER = "IMPORTER"
    COUNTRY_OF_ORIGIN = "COUNTRY_OF_ORIGIN"
    NET_QUANTITY = "NET_QUANTITY"
    MRP = "MRP"
    PACKING_DATE = "PACKING_DATE"
    MANUFACTURE_DATE = "MANUFACTURE_DATE"
    BEST_BEFORE = "BEST_BEFORE"
    USE_BY = "USE_BY"
    CONSUMER_CARE = "CONSUMER_CARE"
    UNIT_SALE_PRICE = "UNIT_SALE_PRICE"


class ExtractionStatus(str, Enum):
    """Extraction outcome classification for a declaration type."""
    FOUND = "FOUND"                    # Authoritative candidate found with high confidence
    MISSING = "MISSING"                # No candidate matched in OCR text
    AMBIGUOUS = "AMBIGUOUS"            # Multiple conflicting candidates detected (requires manual review)
    LOW_CONFIDENCE = "LOW_CONFIDENCE"  # Candidate found but confidence is below reliability threshold


class ExtractionCandidate(BaseModel):
    """
    Individual declaration candidate matched from an OCR text item.
    Retains complete traceability back to the exact OCR line, bounding box, and image.
    """
    model_config = ConfigDict(from_attributes=True)

    declaration_type: DeclarationType = Field(..., description="Target declaration type")
    raw_value: str = Field(..., description="Unmodified extracted substring")
    normalized_value: Optional[str] = Field(None, description="Cleaned, normalized canonical representation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")
    original_ocr_text: str = Field(..., description="Full original OCR line where match occurred")
    source_image_id: Optional[Union[int, str]] = Field(None, description="Identifier of the source image")
    bounding_box: Optional[OCRBoundingBox] = Field(None, description="Bounding box of the source OCR text item")
    page_or_region_id: Optional[str] = Field(None, description="Page or panel region identifier")
    pattern_name: str = Field(..., description="Identifier of regex/heuristic pattern that matched")
    is_ambiguous: bool = Field(default=False, description="Whether this candidate conflicts with another")
    ambiguity_reason: Optional[str] = Field(None, description="Detailed explanation if marked ambiguous")


class ExtractedDeclaration(BaseModel):
    """
    Consolidated declaration result for a specific declaration type.
    Includes the selected authoritative value (if unambiguous and high confidence)
    plus all competing candidate matches.
    """
    model_config = ConfigDict(from_attributes=True)

    declaration_type: DeclarationType = Field(..., description="Declaration type")
    status: ExtractionStatus = Field(..., description="Extraction status (FOUND, MISSING, AMBIGUOUS, LOW_CONFIDENCE)")
    value: Optional[str] = Field(None, description="Best extracted value (None if missing or ambiguous)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence of extracted value")
    candidates: List[ExtractionCandidate] = Field(default_factory=list, description="All extracted candidates")
    source_image_id: Optional[Union[int, str]] = Field(None, description="Source image identifier")
    bounding_box: Optional[OCRBoundingBox] = Field(None, description="Bounding box of the primary match")
    original_ocr_text: Optional[str] = Field(None, description="Original source OCR line for evidence")
    notes: Optional[str] = Field(None, description="Diagnostic notes or manual review guidance")


class DeclarationExtractionResult(BaseModel):
    """
    Full structured extraction output across all 13 declaration types for an inspection session or image.
    Decoupled from legal compliance evaluation.
    """
    model_config = ConfigDict(from_attributes=True)

    image_id: Optional[Union[int, str]] = Field(None, description="Source image identifier")
    declarations: Dict[DeclarationType, ExtractedDeclaration] = Field(
        default_factory=dict,
        description="Extracted results keyed by declaration type"
    )
    all_candidates: List[ExtractionCandidate] = Field(
        default_factory=list,
        description="Flat list of all candidate extractions"
    )
    summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of FOUND, MISSING, AMBIGUOUS, LOW_CONFIDENCE declarations"
    )
    has_ambiguities: bool = Field(
        default=False,
        description="True if any declaration type has multiple conflicting candidates"
    )
    overall_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall OCR/extraction scan confidence"
    )
