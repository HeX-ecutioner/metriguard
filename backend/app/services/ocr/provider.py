"""
Abstract OCR Provider Base Class.
Establishes a unified interface for text detection and recognition engines
(PaddleOCR, Mock, Tesseract, etc.) without coupling to regulatory logic.
"""

from abc import ABC, abstractmethod
from typing import List
import numpy as np
from app.models.ocr_schemas import OCRItem


class OCRProvider(ABC):
    """
    Abstract interface for OCR inference providers.
    Every provider must take a preprocessed numpy image (BGR or Grayscale)
    and return a list of normalized OCRItem objects.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical identifier for this provider (e.g. 'paddleocr', 'mock_ocr')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider dependencies are installed and operational."""
        pass

    @abstractmethod
    def infer(self, image: np.ndarray, timeout_seconds: float = 30.0) -> List[OCRItem]:
        """
        Executes text recognition and detection on the provided image.

        Args:
            image: numpy.ndarray image array (OpenCV format: BGR uint8 or Grayscale uint8).
            timeout_seconds: Maximum allowed execution time before timing out.

        Returns:
            List of normalized OCRItem instances containing text, confidence, and bounding box.

        Raises:
            OCRTimeoutError: If inference exceeds timeout_seconds.
            OCRProviderError: If the underlying model execution fails unexpectedly.
        """
        pass
