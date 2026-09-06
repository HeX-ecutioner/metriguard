"""
PaddleOCR Provider Implementation.
Isolates PaddleOCR dependency and handles native Windows executor issues gracefully.

Known Native Windows Upstream Issue Documented:
Under Windows x64 with paddlepaddle 3.3.1 / paddleocr 3.7.0, CPU execution using oneDNN
currently triggers:
  NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
This provider isolates this error and converts it into a structured OCRProviderError.
"""

import os
import logging
from typing import List, Optional
import numpy as np

from app.models.ocr_schemas import (
    OCRItem,
    OCRBoundingBox,
    OCRProviderError,
)
from app.services.ocr.provider import OCRProvider

logger = logging.getLogger(__name__)


class PaddleOCRProvider(OCRProvider):
    """
    Adapter for Baidu PaddleOCR (PP-OCRv4 / PP-OCRv6) engine.
    Imports and initializes lazily to avoid global side-effects.
    """

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._engine = None
        self._initialization_attempted = False
        self._initialization_error: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "paddleocr"

    def _init_engine(self) -> bool:
        if self._initialization_attempted:
            return self._engine is not None

        self._initialization_attempted = True
        try:
            # Configure environment variables to mitigate oneDNN/PIR issues where possible
            os.environ["FLAGS_enable_pir_api"] = "0"
            os.environ["FLAGS_use_mkldnn"] = "0"

            from paddleocr import PaddleOCR
            try:
                self._engine = PaddleOCR(device="cpu", lang=self.lang)
            except TypeError:
                self._engine = PaddleOCR(use_angle_cls=False, lang=self.lang)

            logger.info("PaddleOCR engine initialized successfully.")
            return True
        except Exception as e:
            self._initialization_error = str(e)
            logger.warning(f"PaddleOCR failed to initialize: {e}")
            return False

    def is_available(self) -> bool:
        """Checks whether PaddleOCR can be imported and initialized."""
        return self._init_engine()

    def infer(self, image: np.ndarray, timeout_seconds: float = 30.0) -> List[OCRItem]:
        """
        Executes PaddleOCR detection and recognition on the preprocessed image.
        """
        if not self._init_engine() or self._engine is None:
            raise OCRProviderError(
                detail=f"PaddleOCR is not operational: {self._initialization_error or 'Engine not initialized.'}"
            )

        try:
            # If grayscale (2D), convert to 3-channel for PaddleOCR detection pipeline
            if len(image.shape) == 2:
                import cv2
                feed_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                feed_img = image

            # Support both PaddleOCR 3.x predict() and legacy ocr()
            if hasattr(self._engine, "predict"):
                raw_result = list(self._engine.predict(feed_img))
            else:
                raw_result = self._engine.ocr(feed_img)

            items: List[OCRItem] = []

            # 1. PaddleOCR 3.x dictionary-like result structure
            if raw_result and hasattr(raw_result[0], "get") and raw_result[0].get("rec_texts") is not None:
                r0 = raw_result[0]
                texts = r0.get("rec_texts", [])
                scores = r0.get("rec_scores", [])
                boxes = r0.get("rec_boxes", [])
                polys = r0.get("rec_polys", [])

                for idx, text in enumerate(texts):
                    conf = float(scores[idx]) if idx < len(scores) else 0.90
                    box_obj = OCRBoundingBox(x=0, y=0, width=0, height=0)

                    if idx < len(boxes) and len(boxes[idx]) >= 4:
                        b = boxes[idx]
                        box_obj = OCRBoundingBox(
                            x=int(b[0]),
                            y=int(b[1]),
                            width=max(0, int(b[2] - b[0])),
                            height=max(0, int(b[3] - b[1]))
                        )
                    elif idx < len(polys) and len(polys[idx]) > 0:
                        xs = [p[0] for p in polys[idx]]
                        ys = [p[1] for p in polys[idx]]
                        box_obj = OCRBoundingBox(
                            x=int(min(xs)),
                            y=int(min(ys)),
                            width=max(0, int(max(xs) - min(xs))),
                            height=max(0, int(max(ys) - min(ys)))
                        )

                    items.append(OCRItem(
                        text=str(text).strip(),
                        confidence=round(conf, 4),
                        bounding_box=box_obj,
                        page_or_region_id="region_0"
                    ))

            # 2. PaddleOCR 2.x legacy structure: [[ [box, (text, conf)], ... ]]
            elif raw_result and isinstance(raw_result, list) and len(raw_result) > 0 and raw_result[0]:
                for line in raw_result[0]:
                    if not line or len(line) < 2:
                        continue
                    box = line[0]
                    text_tuple = line[1]
                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]

                    items.append(OCRItem(
                        text=str(text_tuple[0]).strip(),
                        confidence=round(float(text_tuple[1]), 4),
                        bounding_box=OCRBoundingBox(
                            x=int(min(x_coords)),
                            y=int(min(y_coords)),
                            width=max(0, int(max(x_coords) - min(x_coords))),
                            height=max(0, int(max(y_coords) - min(y_coords)))
                        ),
                        page_or_region_id="region_0"
                    ))

            return items

        except NotImplementedError as nie:
            # Documented Windows PIR oneDNN limitation
            err_msg = (
                f"PaddleOCR runtime error on Windows x64 (Paddle PIR oneDNN attribute defect): {str(nie)}"
            )
            logger.error(err_msg)
            raise OCRProviderError(detail=err_msg)
        except Exception as e:
            logger.error(f"Error during PaddleOCR inference: {e}")
            raise OCRProviderError(detail=f"PaddleOCR execution failed: {str(e)}")
