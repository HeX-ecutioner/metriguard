import logging
import os
import io
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Development fallback toggle, configurable via environment variable
USE_MOCK_EXTRACTOR = os.getenv("USE_MOCK_EXTRACTOR", "false").lower() in ("true", "1", "yes")

_ocr_engine = None


def _get_tesseract_ocr(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Tesseract OCR extraction (lightweight engine)"""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        extracted_data = []
        n_boxes = len(data.get("text", []))
        for i in range(n_boxes):
            text = str(data["text"][i]).strip()
            conf = float(data["conf"][i])
            if text and conf > 0:
                extracted_data.append({
                    "text": text,
                    "confidence": round(conf / 100.0, 2),
                    "box": {
                        "x": int(data["left"][i]),
                        "y": int(data["top"][i]),
                        "width": int(data["width"][i]),
                        "height": int(data["height"][i])
                    }
                })
        return extracted_data
    except Exception as e:
        logger.debug(f"Pytesseract not available or error: {e}")
        return []


def _get_paddle_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            os.environ['FLAGS_enable_pir_api'] = '0'
            os.environ['FLAGS_use_mkldnn'] = '0'
            from paddleocr import PaddleOCR
            try:
                _ocr_engine = PaddleOCR(enable_mkldnn=False, lang='en')
            except TypeError:
                _ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
        except Exception as e:
            logger.warning(f"PaddleOCR not available or failed to initialize: {e}")
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
    Tries Tesseract OCR first, then PaddleOCR, and falls back to mock data only if no engine is installed.
    """
    if USE_MOCK_EXTRACTOR:
        logger.info("Using mock AI extraction (USE_MOCK_EXTRACTOR=true).")
        return get_mock_data()

    # Try Tesseract OCR
    tess_results = _get_tesseract_ocr(image_bytes)
    if tess_results:
        return tess_results

    # Try PaddleOCR
    ocr = _get_paddle_ocr_engine()
    if ocr is not None:
        try:
            import numpy as np
            import cv2

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Pillow fallback if OpenCV fails to decode format
            if img is None:
                try:
                    from PIL import Image
                    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception as img_err:
                    logger.warning(f"Failed to decode image with Pillow fallback: {img_err}")

            if img is None:
                logger.warning("Provided bytes could not be decoded as a valid image.")
                return []

            # Support both PaddleOCR 3.x predict() and legacy ocr()
            if hasattr(ocr, "predict"):
                raw_result = list(ocr.predict(img))
            else:
                raw_result = ocr.ocr(img)

            extracted_data = []

            # PaddleOCR 3.x (PaddleX OCRResult dictionary-like object)
            if raw_result and hasattr(raw_result[0], "get") and raw_result[0].get("rec_texts") is not None:
                r0 = raw_result[0]
                texts = r0.get("rec_texts", [])
                scores = r0.get("rec_scores", [])
                boxes = r0.get("rec_boxes", [])
                polys = r0.get("rec_polys", [])

                for i, text in enumerate(texts):
                    conf = float(scores[i]) if i < len(scores) else 0.95
                    box_dict = {"x": 0, "y": 0, "width": 0, "height": 0}
                    if i < len(boxes) and len(boxes[i]) >= 4:
                        b = boxes[i]
                        box_dict = {
                            "x": int(b[0]),
                            "y": int(b[1]),
                            "width": max(0, int(b[2] - b[0])),
                            "height": max(0, int(b[3] - b[1]))
                        }
                    elif i < len(polys) and len(polys[i]) > 0:
                        xs = [p[0] for p in polys[i]]
                        ys = [p[1] for p in polys[i]]
                        box_dict = {
                            "x": int(min(xs)),
                            "y": int(min(ys)),
                            "width": max(0, int(max(xs) - min(xs))),
                            "height": max(0, int(max(ys) - min(ys)))
                        }
                    extracted_data.append({
                        "text": str(text),
                        "confidence": round(conf, 2),
                        "box": box_dict
                    })

            # PaddleOCR 2.x legacy structure: [[ [box, (text, conf)], ... ]]
            elif raw_result and isinstance(raw_result, list) and len(raw_result) > 0 and raw_result[0]:
                for line in raw_result[0]:
                    if not line or len(line) < 2:
                        continue
                    box = line[0]
                    text_tuple = line[1]
                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]
                    extracted_data.append({
                        "text": str(text_tuple[0]),
                        "confidence": float(text_tuple[1]),
                        "box": {
                            "x": int(min(x_coords)),
                            "y": int(min(y_coords)),
                            "width": max(0, int(max(x_coords) - min(x_coords))),
                            "height": max(0, int(max(y_coords) - min(y_coords)))
                        }
                    })

            return extracted_data
        except Exception as e:
            logger.error(f"Error during PaddleOCR processing: {e}")
            return []

    logger.warning("No OCR engine available. Falling back to mock data.")
    return get_mock_data()
