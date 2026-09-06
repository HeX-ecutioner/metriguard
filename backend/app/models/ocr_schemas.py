"""
Pydantic schemas and error models for MetriGuard OCR subsystem.
Contains strict types for image ID, text lines, confidence scores, bounding boxes,
preprocessing metadata, provider identifiers, and processing durations.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class OCRBoundingBox(BaseModel):
    """Normalized or pixel coordinate bounding box for detected text region."""
    x: int = Field(..., description="Top-left X coordinate in pixels")
    y: int = Field(..., description="Top-left Y coordinate in pixels")
    width: int = Field(..., description="Width of bounding box in pixels")
    height: int = Field(..., description="Height of bounding box in pixels")


class OCRItem(BaseModel):
    """Discrete text element detected by OCR engine."""
    text: str = Field(..., description="Recognized text string")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    bounding_box: OCRBoundingBox = Field(..., description="Bounding box coordinates")
    page_or_region_id: Optional[str] = Field(None, description="Identifier for page, panel, or region")


class PreprocessingMetadata(BaseModel):
    """Detailed audit trail of OpenCV preprocessing stages applied to the input image."""
    original_width: int
    original_height: int
    resized: bool = False
    resized_width: Optional[int] = None
    resized_height: Optional[int] = None
    grayscale: bool = False
    contrast_enhanced: bool = False
    contrast_method: Optional[str] = None  # e.g., "CLAHE"
    denoised: bool = False
    denoise_method: Optional[str] = None   # e.g., "bilateral_filter"


class OCRResult(BaseModel):
    """
    Standardized, normalized OCR processing result.
    Completely decoupled from legal metrology compliance determinations.
    """
    model_config = ConfigDict(from_attributes=True)

    image_id: Union[int, str] = Field(..., description="Identifier of the package image")
    recognized_text: str = Field(..., description="Full consolidated recognized text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall aggregate confidence score")
    items: List[OCRItem] = Field(default_factory=list, description="List of recognized text items with boxes")
    bounding_box: Optional[OCRBoundingBox] = Field(None, description="Outer envelope bounding box")
    page_or_region_id: Optional[str] = Field(None, description="Region or panel identifier if applicable")
    preprocessing_metadata: PreprocessingMetadata = Field(..., description="Metadata from preprocessing stages")
    provider_name: str = Field(..., description="Name of OCR provider used (e.g., mock_ocr, paddleocr)")
    processing_duration_ms: float = Field(..., ge=0.0, description="Total pipeline execution duration in ms")
    is_low_confidence: bool = Field(default=False, description="Flag indicating confidence below threshold")
    warning: Optional[str] = Field(None, description="Warning message if degraded processing occurred")


# Domain Exceptions for OCR Pipeline
class OCRError(Exception):
    """Base exception for all OCR subsystem errors."""
    def __init__(self, detail: str, status_code: int = 500, error_code: str = "OCR_ERROR"):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code


class UnreadableImageError(OCRError):
    """Raised when image bytes cannot be decoded by OpenCV or image parser."""
    def __init__(self, detail: str = "Image could not be read or decoded.", status_code: int = 400):
        super().__init__(detail=detail, status_code=status_code, error_code="UNREADABLE_IMAGE")


class UnsupportedImageFormatError(OCRError):
    """Raised when image file format or channel structure is not supported."""
    def __init__(self, detail: str = "Unsupported image format or color space.", status_code: int = 400):
        super().__init__(detail=detail, status_code=status_code, error_code="UNSUPPORTED_IMAGE_FORMAT")


class ImageNotFoundError(OCRError):
    """Raised when an image file or database reference is missing."""
    def __init__(self, detail: str = "Image file not found.", status_code: int = 404):
        super().__init__(detail=detail, status_code=status_code, error_code="IMAGE_NOT_FOUND")


class OCRTimeoutError(OCRError):
    """Raised when OCR provider inference exceeds maximum allowed duration."""
    def __init__(self, detail: str = "OCR inference timed out.", status_code: int = 504):
        super().__init__(detail=detail, status_code=status_code, error_code="OCR_TIMEOUT")


class OCRProviderError(OCRError):
    """Raised when OCR provider engine fails unexpectedly."""
    def __init__(self, detail: str = "OCR provider failed during inference.", status_code: int = 500):
        super().__init__(detail=detail, status_code=status_code, error_code="OCR_PROVIDER_FAILURE")
