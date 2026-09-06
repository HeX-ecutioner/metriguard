"""
MetriGuard OCR Subsystem Package.
Provides image preprocessing, provider abstraction, mock and production OCR engines,
and normalization decoupled from legal compliance evaluation.
"""

from app.models.ocr_schemas import (
    OCRResult,
    OCRItem,
    OCRBoundingBox,
    PreprocessingMetadata,
    OCRError,
    UnreadableImageError,
    UnsupportedImageFormatError,
    ImageNotFoundError,
    OCRTimeoutError,
    OCRProviderError,
)
from app.services.ocr.provider import OCRProvider
from app.services.ocr.preprocessor import ImagePreprocessor
from app.services.ocr.mock_provider import MockOCRProvider
from app.services.ocr.paddle_provider import PaddleOCRProvider
from app.services.ocr.factory import get_ocr_provider
from app.services.ocr.service import OCRService, get_ocr_service

__all__ = [
    "OCRResult",
    "OCRItem",
    "OCRBoundingBox",
    "PreprocessingMetadata",
    "OCRError",
    "UnreadableImageError",
    "UnsupportedImageFormatError",
    "ImageNotFoundError",
    "OCRTimeoutError",
    "OCRProviderError",
    "OCRProvider",
    "ImagePreprocessor",
    "MockOCRProvider",
    "PaddleOCRProvider",
    "get_ocr_provider",
    "OCRService",
    "get_ocr_service",
]
