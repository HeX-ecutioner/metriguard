"""
OCR Service & Pipeline Orchestrator.
Executes all 9 stages of the MetriGuard OCR pipeline:
1. Load image (bytes or filesystem/storage path)
2. Validate image structure and dimensions
3. Optional aspect-preserving resizing
4. Grayscale conversion
5. Contrast enhancement (CLAHE)
6. Denoising (Bilateral filtering)
7. OCR inference via active OCRProvider
8. Normalize output into comprehensive OCRResult schema
9. Optional persistence into SQLite Declarations table (declaration_type='ocr_text')

Guarantees complete separation of concerns: DOES NOT make any legal compliance decisions.
"""

import time
import logging
from typing import Optional, Union, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ocr_schemas import (
    OCRResult,
    OCRItem,
    OCRBoundingBox,
    OCRError,
    UnreadableImageError,
    UnsupportedImageFormatError,
    ImageNotFoundError,
    OCRTimeoutError,
    OCRProviderError,
)
from app.services.ocr.provider import OCRProvider
from app.services.ocr.preprocessor import ImagePreprocessor
from app.services.ocr.factory import get_ocr_provider
from app.services.storage import get_storage_service
from app.db.crud import add_declaration

logger = logging.getLogger(__name__)


class OCRService:
    """
    Coordinates end-to-end OCR processing, input validation, image preprocessing,
    provider abstraction, and result normalization.
    """

    def __init__(
        self,
        provider: Optional[OCRProvider] = None,
        preprocessor: Optional[ImagePreprocessor] = None,
        confidence_threshold: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.provider = provider or get_ocr_provider()
        self.preprocessor = preprocessor or ImagePreprocessor(
            max_dimension=settings.OCR_MAX_IMAGE_DIMENSION
        )
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.OCR_CONFIDENCE_THRESHOLD
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.OCR_TIMEOUT_SECONDS
        )

    def process_image(
        self,
        image_input: Union[bytes, str],
        image_id: Union[int, str] = "image_0",
        inspection_id: Optional[int] = None,
        db: Optional[Session] = None,
        page_or_region_id: Optional[str] = None,
    ) -> OCRResult:
        """
        Executes the full 9-stage OCR pipeline on an image.

        Args:
            image_input: Raw image bytes, or storage file_key / path string.
            image_id: Identifier for the package image.
            inspection_id: Optional inspection session ID for database persistence.
            db: Optional database session to record raw declarations.
            page_or_region_id: Optional region/panel identifier.

        Returns:
            OCRResult: Fully normalized OCR result containing detected text items,
                       bounding boxes, confidence scores, and preprocessing audit metadata.

        Raises:
            ImageNotFoundError: If a file path or storage key does not exist.
            UnreadableImageError: If the image bytes cannot be decoded.
            UnsupportedImageFormatError: If the image dimensions or format are invalid.
            OCRTimeoutError: If the OCR inference times out.
            OCRProviderError: If the OCR engine crashes.
        """
        start_time = time.perf_counter()

        # Stage 1: Load image data
        image_bytes: bytes
        if isinstance(image_input, (str,)):
            # Check if input is a storage key or filesystem path
            storage = get_storage_service()
            file_path = storage.get_file_path(image_input)
            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        image_bytes = f.read()
                except Exception as e:
                    raise ImageNotFoundError(f"Failed to read image file from storage: {e}")
            else:
                raise ImageNotFoundError(f"Image key '{image_input}' was not found in storage.")
        elif isinstance(image_input, (bytes, bytearray)):
            image_bytes = bytes(image_input)
        else:
            raise UnreadableImageError("Input must be raw bytes or a storage file path string.")

        if not image_bytes or len(image_bytes) == 0:
            raise UnreadableImageError("Provided image payload is empty (0 bytes).")

        # Stages 2 through 6: Validation, Resizing, Grayscale, CLAHE Contrast, Bilateral Denoising
        try:
            preprocessed_img, preproc_meta = self.preprocessor.preprocess(image_bytes)
        except (UnreadableImageError, UnsupportedImageFormatError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error during image preprocessing: {e}")
            raise UnreadableImageError(f"Image preprocessing failed: {str(e)}")

        # Stage 7: OCR Inference via Provider
        items: List[OCRItem] = []
        warning_msg: Optional[str] = None

        try:
            items = self.provider.infer(
                image=preprocessed_img,
                timeout_seconds=self.timeout_seconds
            )
        except OCRTimeoutError:
            logger.warning(f"OCR inference timed out after {self.timeout_seconds}s for image {image_id}.")
            raise
        except OCRProviderError as pe:
            logger.error(f"OCR provider '{self.provider.provider_name}' failed for image {image_id}: {pe.detail}")
            raise
        except Exception as unexp_err:
            logger.error(f"Unexpected provider failure: {unexp_err}")
            raise OCRProviderError(detail=f"OCR provider unexpected failure: {str(unexp_err)}")

        # Stage 8: Normalize OCR Output
        # Calculate consolidated text
        consolidated_text = " ".join(item.text for item in items).strip()

        # Calculate aggregate confidence
        if items:
            avg_confidence = round(sum(item.confidence for item in items) / len(items), 4)
        else:
            avg_confidence = 0.0
            warning_msg = "No text detected in image."

        # Compute outer bounding box envelope
        envelope_box: Optional[OCRBoundingBox] = None
        if items:
            min_x = min(item.bounding_box.x for item in items)
            min_y = min(item.bounding_box.y for item in items)
            max_x = max(item.bounding_box.x + item.bounding_box.width for item in items)
            max_y = max(item.bounding_box.y + item.bounding_box.height for item in items)
            envelope_box = OCRBoundingBox(
                x=min_x,
                y=min_y,
                width=max(0, max_x - min_x),
                height=max(0, max_y - min_y)
            )

        is_low_conf = bool(items and avg_confidence < self.confidence_threshold)
        if is_low_conf:
            warning_msg = (
                f"Low OCR confidence detected ({avg_confidence * 100:.1f}% < "
                f"{self.confidence_threshold * 100:.1f}% threshold)."
            )

        # Calculate duration
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Construct final OCRResult
        result = OCRResult(
            image_id=image_id,
            recognized_text=consolidated_text,
            confidence=avg_confidence,
            items=items,
            bounding_box=envelope_box,
            page_or_region_id=page_or_region_id,
            preprocessing_metadata=preproc_meta,
            provider_name=self.provider.provider_name,
            processing_duration_ms=elapsed_ms,
            is_low_confidence=is_low_conf,
            warning=warning_msg,
        )

        # Stage 9: Optional Database Persistence of Raw Declarations
        if db is not None and inspection_id is not None:
            try:
                from app.db.models import PackageImage
                valid_image_id = None
                if isinstance(image_id, int):
                    img_exists = db.query(PackageImage).filter(
                        PackageImage.id == image_id,
                        PackageImage.inspection_id == inspection_id
                    ).first()
                    if img_exists:
                        valid_image_id = image_id

                for item in items:
                    add_declaration(
                        db=db,
                        inspection_id=inspection_id,
                        declaration_type="ocr_text",
                        extracted_value=item.text,
                        confidence=item.confidence,
                        source_image_id=valid_image_id,
                        bounding_box=item.bounding_box.model_dump(),
                    )
            except Exception as db_err:
                logger.warning(f"Could not persist OCR declarations to database: {db_err}")
                db.rollback()

        return result


def get_ocr_service() -> OCRService:
    """Dependency provider returning an initialized OCRService."""
    return OCRService()
