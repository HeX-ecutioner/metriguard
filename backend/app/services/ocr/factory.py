"""
OCR Provider Factory.
Instantiates and configures the appropriate OCRProvider implementation
based on environment configuration and engine availability.
"""

import logging
from typing import Optional
from app.core.config import settings
from app.services.ocr.provider import OCRProvider
from app.services.ocr.mock_provider import MockOCRProvider
from app.services.ocr.paddle_provider import PaddleOCRProvider

logger = logging.getLogger(__name__)


def get_ocr_provider(provider_name: Optional[str] = None) -> OCRProvider:
    """
    Returns an OCRProvider instance based on the requested name or configuration.

    Args:
        provider_name: Optional explicit provider name ('mock', 'paddleocr', 'auto').
                       If omitted, uses settings.OCR_PROVIDER.

    Returns:
        OCRProvider: Configured, ready-to-use OCR provider.
    """
    target = (provider_name or settings.OCR_PROVIDER).lower().strip()

    if target in ("mock", "mock_ocr"):
        return MockOCRProvider()

    if target == "paddleocr":
        return PaddleOCRProvider()

    # 'auto': Attempt production PaddleOCR, but gracefully fallback to MockOCRProvider if unavailable
    if target == "auto":
        paddle = PaddleOCRProvider()
        if paddle.is_available():
            # Test if PIR defect occurs or if it works
            try:
                import numpy as np
                dummy = np.full((50, 150, 3), 255, dtype=np.uint8)
                paddle.infer(dummy)
                logger.info("Auto-selected operational PaddleOCR provider.")
                return paddle
            except Exception as e:
                logger.warning(
                    f"PaddleOCR is installed but not operational on this system ({e}). "
                    f"Falling back to MockOCRProvider."
                )
                return MockOCRProvider()
        else:
            logger.info("PaddleOCR not available. Using MockOCRProvider.")
            return MockOCRProvider()

    logger.warning(f"Unknown OCR provider '{target}'. Falling back to MockOCRProvider.")
    return MockOCRProvider()
