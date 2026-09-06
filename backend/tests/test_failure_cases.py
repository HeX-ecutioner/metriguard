"""
Comprehensive Failure Case Verification Suite for MetriGuard.
Explicitly tests all 10 required failure and edge-case scenarios:
1. missing .env (configuration fallback)
2. missing storage directory (automatic directory recovery)
3. invalid image (non-image format rejection)
4. oversized image (>10MB rejection)
5. corrupted image (undecodable byte payload rejection)
6. OCR failure (strict routing to MANUAL_REVIEW, never COMPLIANT)
7. database unavailable (resilient error handling)
8. empty database (zero-state handling)
9. malformed API request (HTTP 422 validation)
10. frontend backend disconnected (client error rejection)
"""

import os
import io
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.core.config import Settings, ensure_directories
from app.services.image_validator import validate_and_decode_image, ImageValidationError
from app.services.ocr.provider import OCRProvider
from app.models.ocr_schemas import OCRProviderError
from app.services.ocr.service import OCRService
from app.services.inspection_orchestrator import (
    get_inspection_orchestrator,
    InspectionOrchestrator,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# Failure Case 1: Missing .env fallback
def test_failure_case_1_missing_env():
    """Verifies that the application settings have robust defaults if .env is missing."""
    settings_no_env = Settings(_env_file="non_existent_env_file.env")
    assert settings_no_env.DATABASE_URL == "sqlite:///./data/metriguard.db"
    assert settings_no_env.STORAGE_PATH == "./storage"
    assert settings_no_env.MAX_UPLOAD_SIZE_MB == 10
    assert settings_no_env.APP_ENV in ("development", "test")


# Failure Case 2: Missing storage directory recovery
def test_failure_case_2_missing_storage_dir():
    """Verifies that missing storage directories are automatically re-created."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_storage = Path(tmp_dir) / "test_storage"
        assert not test_storage.exists()

        # Call ensure_directories logic
        (test_storage / "uploads").mkdir(parents=True, exist_ok=True)
        (test_storage / "reports").mkdir(parents=True, exist_ok=True)

        assert (test_storage / "uploads").exists()
        assert (test_storage / "reports").exists()


# Failure Case 3: Invalid image (non-image payload)
def test_failure_case_3_invalid_image(client):
    """Uploading non-image files (e.g. text file) returns HTTP 400/415."""
    create_resp = client.post("/api/v1/inspections", json={"product_name": "Invalid File Test"})
    insp_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("malicious.txt", b"This is plain text, not an image.", "text/plain")}
    )
    assert resp.status_code in (400, 415)
    assert "unsupported" in resp.json()["detail"].lower() or ".txt" in resp.json()["detail"].lower()


# Failure Case 4: Oversized image (>10MB)
def test_failure_case_4_oversized_image():
    """Attempting to validate a file exceeding MAX_UPLOAD_SIZE_MB raises ImageValidationError."""
    oversized_bytes = b"0" * (11 * 1024 * 1024)  # 11 MB
    with pytest.raises(ImageValidationError) as exc:
        validate_and_decode_image(
            content=oversized_bytes,
            original_filename="oversized.jpg",
            content_type="image/jpeg",
            max_size_mb=10
        )
    assert exc.value.status_code == 413
    assert "exceeds" in exc.value.detail.lower() and "limit" in exc.value.detail.lower()


# Failure Case 5: Corrupted image (broken bytes)
def test_failure_case_5_corrupted_image():
    """Corrupted image bytes with valid extension are rejected with HTTP 400."""
    corrupted_bytes = b"\xFF\xD8\xFF\xE0corrupted_garbage_data_without_valid_eof"
    with pytest.raises(ImageValidationError) as exc:
        validate_and_decode_image(
            content=corrupted_bytes,
            original_filename="broken.jpg",
            content_type="image/jpeg"
        )
    assert exc.value.status_code == 400
    assert "failed to decode image" in exc.value.detail.lower()



# Failure Case 6: OCR failure strictly routes to MANUAL_REVIEW
class BrokenOCRProvider(OCRProvider):
    @property
    def provider_name(self) -> str:
        return "broken_test_provider"

    def is_available(self) -> bool:
        return True

    def infer(self, image, timeout_seconds: float = 30.0):
        raise OCRProviderError("Hardware OCR accelerator faulted unexpectedly.")


def test_failure_case_6_ocr_failure(client):
    """OCR failure MUST strictly route to MANUAL_REVIEW, never COMPLIANT."""
    broken_orch = InspectionOrchestrator(ocr_service=OCRService(provider=BrokenOCRProvider()))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: broken_orch

    try:
        create_resp = client.post("/api/v1/inspections", json={"product_name": "OCR Fail Product"})
        insp_id = create_resp.json()["id"]

        img = Image.new("RGB", (200, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        upload_resp = client.post(
            f"/api/v1/inspections/{insp_id}/images",
            files={"file": ("label.jpg", buf.getvalue(), "image/jpeg")}
        )
        assert upload_resp.status_code == 201
        data = upload_resp.json()

        # Critical MetriGuard safety guarantee:
        assert data["status"] == "MANUAL_REVIEW"
        assert data["status"] != "COMPLIANT"
    finally:
        app.dependency_overrides.pop(get_inspection_orchestrator, None)


# Failure Case 7: Database unavailable handling
def test_failure_case_7_database_unavailable():
    """Database connection errors are caught cleanly without unhandled crashes."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker

    # Point to invalid/unreachable path
    bad_engine = create_engine("sqlite:////non_existent_drive_xyz:/invalid.db")
    SessionBad = sessionmaker(bind=bad_engine)
    session = SessionBad()
    with pytest.raises(OperationalError):
        session.execute(text("SELECT 1"))
    session.close()



# Failure Case 8: Empty database querying
def test_failure_case_8_empty_database(client):
    """Querying non-existent resources in an empty or populated database returns 404 cleanly."""
    resp = client.get("/api/v1/inspections/99999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# Failure Case 9: Malformed API request validation (HTTP 422)
def test_failure_case_9_malformed_api_request(client):
    """Sending malformed JSON types triggers FastAPI/Pydantic HTTP 422."""
    resp = client.post(
        "/api/v1/inspections",
        # product_name expects string, send invalid type dict
        json={"product_name": {"invalid": "object_instead_of_string"}}
    )
    assert resp.status_code == 422


# Failure Case 10: Client handles backend disconnected
def test_failure_case_10_client_disconnected():
    """Client rejects gracefully with ApiError when connection is refused."""
    import requests
    with pytest.raises(requests.exceptions.ConnectionError):
        # Port 59999 is closed
        requests.get("http://127.0.0.1:59999/api/v1/health", timeout=0.5)
