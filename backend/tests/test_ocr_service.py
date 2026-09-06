"""
Comprehensive Test Suite for MetriGuard OCR Subsystem.
Tests OpenCV preprocessing, provider abstraction, mock provider, PaddleOCR isolation,
normalization, database persistence, failure modes, and API endpoints.
Strictly verifies that the OCR layer does NOT perform legal compliance determinations.
"""

import io
import pytest
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.models.ocr_schemas import (
    OCRResult,
    OCRItem,
    OCRBoundingBox,
    UnreadableImageError,
    UnsupportedImageFormatError,
    ImageNotFoundError,
    OCRTimeoutError,
    OCRProviderError,
)
from app.services.ocr.preprocessor import ImagePreprocessor
from app.services.ocr.mock_provider import MockOCRProvider
from app.services.ocr.paddle_provider import PaddleOCRProvider
from app.services.ocr.service import OCRService
from app.db.database import get_db, Base, engine
from app.db.models import Inspection, PackageImage, Declaration

client = TestClient(app)


def make_test_image_bytes(size=(320, 240), color=(255, 255, 255), format="JPEG") -> bytes:
    """Helper to generate in-memory test image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


# ============================================================================
# 1. OpenCV Preprocessor Tests (Stages 1 - 6)
# ============================================================================

def test_preprocessor_load_and_validate_valid_image():
    """Verify loading, validation, grayscale, CLAHE, and denoising stages."""
    img_bytes = make_test_image_bytes(size=(400, 300))
    preprocessor = ImagePreprocessor()

    processed_img, meta = preprocessor.preprocess(img_bytes)

    assert isinstance(processed_img, np.ndarray)
    assert processed_img.dtype == np.uint8
    assert len(processed_img.shape) == 2  # Grayscale
    assert meta.original_width == 400
    assert meta.original_height == 300
    assert meta.resized is False
    assert meta.grayscale is True
    assert meta.contrast_enhanced is True
    assert meta.contrast_method == "CLAHE"
    assert meta.denoised is True
    assert meta.denoise_method == "bilateral_filter"


def test_preprocessor_resizes_oversized_image():
    """Verify aspect-preserving resize on images exceeding max_dimension."""
    # 3000 x 1500 image with 2:1 aspect ratio
    img_bytes = make_test_image_bytes(size=(3000, 1500))
    preprocessor = ImagePreprocessor(max_dimension=2000)

    processed_img, meta = preprocessor.preprocess(img_bytes)

    assert meta.resized is True
    assert meta.resized_width == 2000
    assert meta.resized_height == 1000  # Preserved 2:1 ratio
    assert processed_img.shape == (1000, 2000)


def test_preprocessor_rejects_unreadable_bytes():
    """Verify UnreadableImageError is raised when provided corrupt or garbage bytes."""
    preprocessor = ImagePreprocessor()
    with pytest.raises(UnreadableImageError) as exc_info:
        preprocessor.preprocess(b"NOT_A_VALID_IMAGE_DATA_STREAM")
    assert "Failed to decode" in exc_info.value.detail or "could not be read" in exc_info.value.detail.lower()


def test_preprocessor_rejects_empty_bytes():
    """Verify UnreadableImageError is raised for 0-byte input."""
    preprocessor = ImagePreprocessor()
    with pytest.raises(UnreadableImageError) as exc_info:
        preprocessor.preprocess(b"")
    assert "Empty image" in exc_info.value.detail


def test_preprocessor_rejects_tiny_image():
    """Verify UnsupportedImageFormatError on sub-minimum dimension image."""
    img_bytes = make_test_image_bytes(size=(8, 8))
    preprocessor = ImagePreprocessor(min_dimension=15)
    with pytest.raises(UnsupportedImageFormatError) as exc_info:
        preprocessor.preprocess(img_bytes)
    assert "too small" in exc_info.value.detail


# ============================================================================
# 2. Provider Abstraction Tests
# ============================================================================

def test_mock_provider_deterministic_inference():
    """Verify MockOCRProvider returns predictable packaged goods text elements."""
    provider = MockOCRProvider()
    assert provider.provider_name == "mock_ocr"
    assert provider.is_available() is True

    dummy_img = np.full((100, 200), 255, dtype=np.uint8)
    items = provider.infer(dummy_img)

    assert len(items) == 4
    texts = [item.text for item in items]
    assert any("MRP" in t for t in texts)
    assert any("Net Wt" in t for t in texts)
    assert all(item.confidence > 0.9 for item in items)
    assert all(item.bounding_box.width > 0 for item in items)


def test_mock_provider_empty_simulation():
    """Verify MockOCRProvider simulates empty detections without crashing."""
    provider = MockOCRProvider(simulate_empty=True)
    dummy_img = np.full((100, 200), 255, dtype=np.uint8)
    items = provider.infer(dummy_img)
    assert items == []


def test_mock_provider_low_confidence_simulation():
    """Verify MockOCRProvider simulates low confidence text elements."""
    provider = MockOCRProvider(simulate_low_confidence=True)
    dummy_img = np.full((100, 200), 255, dtype=np.uint8)
    items = provider.infer(dummy_img)
    assert len(items) > 0
    assert all(item.confidence < 0.5 for item in items)


def test_mock_provider_timeout_simulation():
    """Verify MockOCRProvider raises OCRTimeoutError when configured."""
    provider = MockOCRProvider(simulate_timeout=True)
    dummy_img = np.full((100, 200), 255, dtype=np.uint8)
    with pytest.raises(OCRTimeoutError) as exc_info:
        provider.infer(dummy_img, timeout_seconds=5.0)
    assert "timed out" in exc_info.value.detail.lower()


def test_mock_provider_failure_simulation():
    """Verify MockOCRProvider raises OCRProviderError on engine failure."""
    provider = MockOCRProvider(simulate_failure=True, failure_message="Engine crash test")
    dummy_img = np.full((100, 200), 255, dtype=np.uint8)
    with pytest.raises(OCRProviderError) as exc_info:
        provider.infer(dummy_img)
    assert "Engine crash test" in exc_info.value.detail


def test_paddle_provider_safe_handling():
    """Verify PaddleOCRProvider isolates errors and provides structured diagnostics."""
    paddle_provider = PaddleOCRProvider()
    assert paddle_provider.provider_name == "paddleocr"
    # Even if PIR executor defect occurs, it must raise OCRProviderError cleanly
    dummy_img = np.full((100, 200, 3), 255, dtype=np.uint8)
    try:
        paddle_provider.infer(dummy_img)
    except OCRProviderError as pe:
        assert "PaddleOCR" in pe.detail


# ============================================================================
# 3. Service Layer & Normalization Tests (Stages 7 - 9)
# ============================================================================

def test_ocr_service_full_pipeline():
    """Verify full 9-stage pipeline and check every field in normalized OCRResult."""
    img_bytes = make_test_image_bytes(size=(640, 480))
    service = OCRService(provider=MockOCRProvider())

    result = service.process_image(
        image_input=img_bytes,
        image_id="package_front_01",
        page_or_region_id="front_panel"
    )

    assert isinstance(result, OCRResult)
    assert result.image_id == "package_front_01"
    assert result.page_or_region_id == "front_panel"
    assert "MRP" in result.recognized_text
    assert "Net Wt" in result.recognized_text
    assert result.confidence > 0.9
    assert len(result.items) == 4
    assert result.bounding_box is not None
    assert result.bounding_box.width > 0
    assert result.bounding_box.height > 0
    assert result.provider_name == "mock_ocr"
    assert result.processing_duration_ms > 0.0
    assert result.is_low_confidence is False
    assert result.warning is None

    # Verify audit metadata
    assert result.preprocessing_metadata.original_width == 640
    assert result.preprocessing_metadata.original_height == 480
    assert result.preprocessing_metadata.grayscale is True
    assert result.preprocessing_metadata.contrast_enhanced is True


def test_ocr_service_handles_empty_ocr_result():
    """Verify graceful handling when no text is detected."""
    img_bytes = make_test_image_bytes()
    service = OCRService(provider=MockOCRProvider(simulate_empty=True))

    result = service.process_image(image_input=img_bytes, image_id="blank_img")

    assert result.recognized_text == ""
    assert result.confidence == 0.0
    assert result.items == []
    assert result.bounding_box is None
    assert result.warning is not None
    assert "No text detected" in result.warning


def test_ocr_service_handles_low_confidence():
    """Verify low confidence OCR is flagged with is_low_confidence=True."""
    img_bytes = make_test_image_bytes()
    service = OCRService(
        provider=MockOCRProvider(simulate_low_confidence=True),
        confidence_threshold=0.60
    )

    result = service.process_image(image_input=img_bytes, image_id="low_conf_img")

    assert result.is_low_confidence is True
    assert result.warning is not None
    assert "Low OCR confidence" in result.warning


def test_ocr_service_missing_image_file():
    """Verify ImageNotFoundError is raised when storage file does not exist."""
    service = OCRService(provider=MockOCRProvider())
    with pytest.raises(ImageNotFoundError) as exc_info:
        service.process_image(image_input="non_existent_uuid_key.jpg")
    assert "not found" in exc_info.value.detail.lower()


def test_ocr_service_handles_provider_timeout():
    """Verify OCRTimeoutError propagates cleanly through service."""
    img_bytes = make_test_image_bytes()
    service = OCRService(provider=MockOCRProvider(simulate_timeout=True))
    with pytest.raises(OCRTimeoutError):
        service.process_image(image_input=img_bytes)


def test_ocr_service_handles_provider_failure():
    """Verify OCRProviderError propagates cleanly through service."""
    img_bytes = make_test_image_bytes()
    service = OCRService(provider=MockOCRProvider(simulate_failure=True))
    with pytest.raises(OCRProviderError):
        service.process_image(image_input=img_bytes)


def test_ocr_service_persists_raw_declarations_without_compliance_decision():
    """
    CRITICAL ARCHITECTURAL TEST:
    Verify that OCR persists raw declarations with declaration_type='ocr_text',
    but DOES NOT create any legal compliance results or violations.
    """
    db = next(get_db())
    try:
        # Create an inspection
        insp = Inspection(status="CREATED", product_name="Test Product OCR")
        db.add(insp)
        db.commit()
        db.refresh(insp)

        # Create an associated package image
        pkg_img = PackageImage(
            inspection_id=insp.id,
            file_path="uploads/test_pack.jpg",
            original_filename="test_pack.jpg",
            mime_type="image/jpeg",
            file_size=1024,
        )
        db.add(pkg_img)
        db.commit()
        db.refresh(pkg_img)

        img_bytes = make_test_image_bytes()
        service = OCRService(provider=MockOCRProvider())

        result = service.process_image(
            image_input=img_bytes,
            image_id=pkg_img.id,
            inspection_id=insp.id,
            db=db
        )

        assert len(result.items) == 4

        # Query database declarations
        decls = db.query(Declaration).filter(Declaration.inspection_id == insp.id).all()
        assert len(decls) == 4
        assert all(d.declaration_type == "ocr_text" for d in decls)
        assert all(d.source_image_id == pkg_img.id for d in decls)

        # STRICT VERIFICATION: Ensure NO compliance results or violations were generated
        assert insp.result is None
        assert len(insp.violations) == 0
        assert insp.status == "CREATED"
    finally:
        db.close()


# ============================================================================
# 4. API Endpoint Tests
# ============================================================================

def test_api_ocr_process_endpoint_success():
    """Verify direct image upload to POST /api/v1/ocr/process."""
    img_bytes = make_test_image_bytes(size=(300, 200))
    response = client.post(
        "/api/v1/ocr/process",
        files={"file": ("label.jpg", img_bytes, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "image_id" in data
    assert "recognized_text" in data
    assert "confidence" in data
    assert "items" in data
    assert len(data["items"]) > 0
    assert "preprocessing_metadata" in data
    assert "provider_name" in data
    assert "processing_duration_ms" in data


def test_api_ocr_process_unreadable_file():
    """Verify POST /api/v1/ocr/process returns 400 on corrupt file payload."""
    response = client.post(
        "/api/v1/ocr/process",
        files={"file": ("corrupt.jpg", b"INVALID_BYTES_NOT_AN_IMAGE", "image/jpeg")}
    )
    assert response.status_code == 400
    assert "could not be decoded" in response.json()["detail"].lower()


def test_api_inspection_image_ocr_flow():
    """Verify running OCR on an image attached to an existing inspection."""
    # 1. Create inspection session
    create_res = client.post("/api/v1/inspections", json={"product_name": "Sunflower Oil"})
    assert create_res.status_code == 201
    inspection_id = create_res.json()["id"]

    # 2. Upload image to inspection
    img_bytes = make_test_image_bytes(size=(400, 300))
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("oil_front.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    image_id = upload_res.json()["id"]

    # 3. Call OCR endpoint on the inspection image
    ocr_res = client.post(f"/api/v1/ocr/inspections/{inspection_id}/images/{image_id}")
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()

    assert ocr_data["image_id"] == image_id
    assert len(ocr_data["items"]) == 4
    assert ocr_data["preprocessing_metadata"]["original_width"] == 400
    assert ocr_data["preprocessing_metadata"]["original_height"] == 300


def test_api_inspection_image_ocr_missing_inspection():
    """Verify 404 response for non-existent inspection session."""
    res = client.post("/api/v1/ocr/inspections/99999999/images/1")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_api_inspection_image_ocr_missing_image():
    """Verify 404 response for non-existent image within an existing inspection."""
    create_res = client.post("/api/v1/inspections", json={"product_name": "Test Item"})
    inspection_id = create_res.json()["id"]

    res = client.post(f"/api/v1/ocr/inspections/{inspection_id}/images/88888888")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
