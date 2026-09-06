import io
import pytest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.services.storage import StorageError, get_storage_service

client = TestClient(app)


def make_test_image(format="JPEG", size=(120, 80), color=(255, 100, 50)) -> bytes:
    """Helper to generate valid in-memory test image bytes."""
    buf = io.BytesIO()
    mode = "RGB" if format.upper() != "PNG" else "RGBA"
    img = Image.new(mode, size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture
def created_inspection():
    """Creates a fresh inspection session via API and returns its ID."""
    res = client.post("/api/v1/inspections", json={"product_name": "Test Biscuit Pack", "notes": "Unit test"})
    assert res.status_code == 201
    return res.json()["id"]


def test_create_inspection():
    """Verify inspection creation endpoint."""
    res = client.post("/api/v1/inspections", json={"product_name": "Sunflower Oil 1L", "notes": "Pouch inspection"})
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["status"] == "CREATED"
    assert data["product_name"] == "Sunflower Oil 1L"
    assert data["notes"] == "Pouch inspection"
    assert isinstance(data["images"], list)
    assert len(data["images"]) == 0


def test_valid_jpeg_upload(created_inspection):
    """Test valid JPEG upload to an existing inspection."""
    jpeg_bytes = make_test_image(format="JPEG", size=(200, 150))
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("front_label.jpg", jpeg_bytes, "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["inspection_id"] == created_inspection
    assert data["original_filename"] == "front_label.jpg"
    assert data["mime_type"] == "image/jpeg"
    assert data["width"] == 200
    assert data["height"] == 150
    assert data["file_size"] == len(jpeg_bytes)
    assert "file_path" in data


def test_valid_png_upload(created_inspection):
    """Test valid PNG upload."""
    png_bytes = make_test_image(format="PNG", size=(300, 200))
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("back_panel.png", png_bytes, "image/png")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mime_type"] == "image/png"
    assert data["width"] == 300
    assert data["height"] == 200


def test_valid_webp_upload(created_inspection):
    """Test valid WebP upload."""
    webp_bytes = make_test_image(format="WEBP", size=(150, 150))
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("side_panel.webp", webp_bytes, "image/webp")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mime_type"] == "image/webp"
    assert data["width"] == 150
    assert data["height"] == 150


def test_invalid_extension(created_inspection):
    """Reject upload when file extension is not allowed."""
    jpeg_bytes = make_test_image(format="JPEG")
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("script.exe", jpeg_bytes, "image/jpeg")}
    )
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


def test_invalid_mime_type(created_inspection):
    """Reject upload when MIME type is not allowed."""
    jpeg_bytes = make_test_image(format="JPEG")
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("sample.jpg", jpeg_bytes, "text/plain")}
    )
    assert res.status_code == 400
    assert "Unsupported MIME type" in res.json()["detail"]


def test_oversized_file(created_inspection, monkeypatch):
    """Reject file exceeding configured MAX_UPLOAD_SIZE_MB."""
    from app.core import config
    # Temporarily set limit to 1MB for fast test execution
    monkeypatch.setattr(config.settings, "MAX_UPLOAD_SIZE_MB", 1)
    large_bytes = b"X" * (2 * 1024 * 1024)  # 2MB
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("large.jpg", large_bytes, "image/jpeg")}
    )
    assert res.status_code == 413
    assert "exceeds the maximum allowed limit" in res.json()["detail"]


def test_corrupted_image(created_inspection):
    """Reject corrupted image bytes that fail decoding."""
    fake_bytes = b"GIF89aNOT_A_VALID_JPEG_HEADER_CORRUPTED"
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("corrupted.jpg", fake_bytes, "image/jpeg")}
    )
    assert res.status_code == 400
    assert "could not be decoded" in res.json()["detail"].lower()


def test_empty_file(created_inspection):
    """Reject 0-byte empty file."""
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("empty.png", b"", "image/png")}
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_missing_inspection():
    """Return 404 when uploading to a non-existent inspection."""
    jpeg_bytes = make_test_image(format="JPEG")
    res = client.post(
        "/api/v1/inspections/99999999/images",
        files={"file": ("label.jpg", jpeg_bytes, "image/jpeg")}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_path_traversal_filename(created_inspection):
    """Prevent path traversal and safely store using sanitized filename."""
    jpeg_bytes = make_test_image(format="JPEG")
    malicious_filename = "../../../../windows/system32/evil_payload.jpg"
    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": (malicious_filename, jpeg_bytes, "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()
    assert ".." not in data["file_path"]
    assert "evil_payload.jpg" in data["file_path"]
    # Verify the file is stored strictly within storage/uploads
    storage = get_storage_service()
    abs_path = storage.get_file_path(data["file_path"])
    assert abs_path is not None
    assert Path(abs_path).is_relative_to(Path(storage.get_file_path("")).resolve())


def test_storage_failure(created_inspection, monkeypatch):
    """Handle storage write failure cleanly with HTTP 500 error."""
    jpeg_bytes = make_test_image(format="JPEG")

    async def mock_save_file(self, filename, content):
        raise StorageError(detail="Simulated disk write failure", error_code="STORAGE_FAILURE", status_code=500)

    from app.services.storage import LocalStorageService
    monkeypatch.setattr(LocalStorageService, "save_file", mock_save_file)

    res = client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("valid.jpg", jpeg_bytes, "image/jpeg")}
    )
    assert res.status_code == 500
    assert "Simulated disk write failure" in res.json()["detail"]


def test_get_inspection_with_images(created_inspection):
    """Verify retrieving an inspection returns all attached images."""
    img1 = make_test_image(format="JPEG")
    img2 = make_test_image(format="PNG")

    client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("img1.jpg", img1, "image/jpeg")}
    )
    client.post(
        f"/api/v1/inspections/{created_inspection}/images",
        files={"file": ("img2.png", img2, "image/png")}
    )

    res = client.get(f"/api/v1/inspections/{created_inspection}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == created_inspection
    assert len(data["images"]) == 2
    filenames = [img["original_filename"] for img in data["images"]]
    assert "img1.jpg" in filenames
    assert "img2.png" in filenames


def test_get_missing_inspection():
    """Verify 404 response for non-existent inspection."""
    res = client.get("/api/v1/inspections/99999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_upload_image_triggers_ocr_and_compliance(created_inspection):
    """Verify image upload triggers OCR and compliance evaluation and returns analysis."""
    from app.api.inspections import get_inspection_orchestrator
    from app.services.inspection_orchestrator import InspectionOrchestrator
    from app.services.ocr.service import OCRService
    from app.services.ocr.mock_provider import MockOCRProvider
    from app.models.ocr_schemas import OCRItem, OCRBoundingBox

    mock_items = [
        OCRItem(
            text="MRP Rs. 150 (Incl. of all taxes)",
            confidence=0.98,
            bounding_box=OCRBoundingBox(x=10, y=10, width=100, height=20)
        ),
        OCRItem(
            text="Net Wt 500g",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=10, y=40, width=80, height=20)
        ),
        OCRItem(
            text="Mfd. by MetriGuard Co.",
            confidence=0.99,
            bounding_box=OCRBoundingBox(x=10, y=70, width=150, height=20)
        ),
        OCRItem(
            text="Mfg. Date 10/2025",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=10, y=100, width=120, height=20)
        ),
    ]
    custom_ocr = OCRService(provider=MockOCRProvider(custom_items=mock_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=custom_ocr
    )

    try:
        img = make_test_image(format="JPEG")
        res = client.post(
            f"/api/v1/inspections/{created_inspection}/images",
            files={"file": ("packaged_item.jpg", img, "image/jpeg")}
        )
        assert res.status_code == 201
        data = res.json()
        assert "status" in data
        assert data["confidence_score"] is not None
        assert len(data["extracted_texts"]) >= 3

        # Also verify that GET /api/v1/inspections/{id} reflects updated state
        detail_res = client.get(f"/api/v1/inspections/{created_inspection}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["status"] is not None
        assert len(detail_data["declarations"]) >= 3
        assert detail_data["result"] is not None
    finally:
        app.dependency_overrides.clear()
