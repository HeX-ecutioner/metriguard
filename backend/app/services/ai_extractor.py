import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Development fallback toggle, configurable via environment variable
USE_MOCK_EXTRACTOR = os.getenv("USE_MOCK_EXTRACTOR", "true").lower() in ("true", "1", "yes")

_ocr_engine = None


def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
        except Exception as e:
            logger.warning(f"PaddleOCR not available or failed to load: {e}. Using mock extraction.")
            return None
    return _ocr_engine


def get_mock_data() -> List[Dict[str, Any]]:
    """Development mock declarations for packaged commodity testing"""
    return [
        {"text": "MRP Rs. 150", "confidence": 0.98, "box": {"x": 10, "y": 10, "width": 100, "height": 20}},
        {"text": "Net Wt 500g", "confidence": 0.95, "box": {"x": 10, "y": 40, "width": 80, "height": 20}},
        {"text": "Mfd. by MetriGuard Co.", "confidence": 0.99, "box": {"x": 10, "y": 70, "width": 150, "height": 20}},
        {"text": "Mfg. Date 10/2025", "confidence": 0.92, "box": {"x": 10, "y": 100, "width": 120, "height": 20}},
    ]


def extract_information(image_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text, bounding boxes, and confidence scores from an image.
    Returns a list of dicts: {'text': str, 'confidence': float, 'box': {'x': int, 'y': int, 'width': int, 'height': int}}
    """
    if USE_MOCK_EXTRACTOR:
        logger.info("Using mock AI extraction (USE_MOCK_EXTRACTOR=true).")
        return get_mock_data()

    ocr = _get_ocr_engine()
    if ocr is None:
        return get_mock_data()

    try:
        import numpy as np
        import cv2

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Could not decode image bytes. Falling back to mock data.")
            return get_mock_data()

        result = ocr.ocr(img, cls=True)

        extracted_data = []
        if result and result[0]:
            for line in result[0]:
                if not line or len(line) < 2:
                    continue
                box = line[0]  # [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                text_tuple = line[1]  # (text, confidence)

                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]

                extracted_data.append({
                    "text": str(text_tuple[0]),
                    "confidence": float(text_tuple[1]),
                    "box": {
                        "x": int(min(x_coords)),
                        "y": int(min(y_coords)),
                        "width": int(max(x_coords) - min(x_coords)),
                        "height": int(max(y_coords) - min(y_coords))
                    }
                })

        return extracted_data
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}. Falling back to mock data.")
        return get_mock_data()
