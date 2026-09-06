"""
Deterministic Mock OCR Provider.
Provides predictable, reproducible OCR inferences for unit tests, local development,
and graceful fallback during native Windows runtime defects.
"""

from typing import List, Optional
import numpy as np
from app.models.ocr_schemas import (
    OCRItem,
    OCRBoundingBox,
    OCRTimeoutError,
    OCRProviderError,
)
from app.services.ocr.provider import OCRProvider


class MockOCRProvider(OCRProvider):
    """
    Deterministic mock provider that can simulate standard packaged commodity declarations,
    empty outputs, low-confidence detections, timeouts, or engine exceptions.
    """

    DEFAULT_ITEMS = [
        OCRItem(
            text="MRP Rs. 150.00 (Incl. of all taxes)",
            confidence=0.98,
            bounding_box=OCRBoundingBox(x=20, y=30, width=280, height=25),
            page_or_region_id="region_0"
        ),
        OCRItem(
            text="Net Wt: 500g",
            confidence=0.96,
            bounding_box=OCRBoundingBox(x=20, y=70, width=140, height=22),
            page_or_region_id="region_0"
        ),
        OCRItem(
            text="Mfd. by MetriGuard Food Products Pvt Ltd",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=20, y=110, width=340, height=24),
            page_or_region_id="region_0"
        ),
        OCRItem(
            text="Mfg. Date: 10/2025",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=20, y=150, width=180, height=22),
            page_or_region_id="region_0"
        ),
    ]

    def __init__(
        self,
        custom_items: Optional[List[OCRItem]] = None,
        simulate_empty: bool = False,
        simulate_low_confidence: bool = False,
        simulate_timeout: bool = False,
        simulate_failure: bool = False,
        failure_message: str = "Mock engine encountered a simulated crash."
    ):
        self.custom_items = custom_items
        self.simulate_empty = simulate_empty
        self.simulate_low_confidence = simulate_low_confidence
        self.simulate_timeout = simulate_timeout
        self.simulate_failure = simulate_failure
        self.failure_message = failure_message

    @property
    def provider_name(self) -> str:
        return "mock_ocr"

    def is_available(self) -> bool:
        return True

    def infer(self, image: np.ndarray, timeout_seconds: float = 30.0) -> List[OCRItem]:
        """
        Executes deterministic mock OCR inference.
        """
        if self.simulate_failure:
            raise OCRProviderError(detail=self.failure_message)

        if self.simulate_timeout:
            raise OCRTimeoutError(detail=f"Mock OCR inference timed out after {timeout_seconds}s.")

        if self.simulate_empty:
            return []

        if self.simulate_low_confidence:
            return [
                OCRItem(
                    text="Blurry text sample #1",
                    confidence=0.25,
                    bounding_box=OCRBoundingBox(x=10, y=10, width=120, height=20),
                    page_or_region_id="region_0"
                ),
                OCRItem(
                    text="Faint batch code ???",
                    confidence=0.35,
                    bounding_box=OCRBoundingBox(x=10, y=40, width=150, height=20),
                    page_or_region_id="region_0"
                ),
            ]

        if self.custom_items is not None:
            return [item.model_copy() for item in self.custom_items]

        return [item.model_copy() for item in self.DEFAULT_ITEMS]
