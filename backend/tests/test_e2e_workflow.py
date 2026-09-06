"""
Comprehensive End-to-End Workflow Tests for MetriGuard MVP.
Verifies the complete Legal Metrology inspection lifecycle across all 9 required scenarios:
1. Successful compliant inspection
2. Non-compliant inspection
3. Manual-review inspection
4. Invalid upload
5. OCR failure
6. Rule-engine failure
7. Missing image
8. Empty database
9. Repeated inspection retrieval
"""

import io
import pytest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.api.inspections import get_inspection_orchestrator
from app.services.inspection_orchestrator import InspectionOrchestrator
from app.services.ocr.service import OCRService
from app.services.ocr.mock_provider import MockOCRProvider
from app.models.ocr_schemas import OCRItem, OCRBoundingBox
from app.services.storage import get_storage_service
from app.services.rules.engine import RuleEngine

client = TestClient(app)


def make_test_image(format="JPEG", size=(200, 150), color=(100, 150, 200)) -> bytes:
    """Generates valid image bytes in memory."""
    buf = io.BytesIO()
    mode = "RGB" if format.upper() != "PNG" else "RGBA"
    img = Image.new(mode, size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    """Ensures dependency overrides are clean before and after every test."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# =========================================================================
# Scenario 1: Successful Compliant Inspection
# =========================================================================
def test_e2e_successful_compliant_inspection():
    """
    User creates an inspection, uploads a compliant package image.
    Backend validates, stores image, extracts declarations, evaluates rules.
    System produces COMPLIANT with zero violations and persisted records.
    """
    compliant_items = [
        OCRItem(
            text="MRP Rs. 150.00 (Incl. of all taxes)",
            confidence=0.98,
            bounding_box=OCRBoundingBox(x=20, y=30, width=280, height=25),
        ),
        OCRItem(
            text="Net Wt: 500g",
            confidence=0.96,
            bounding_box=OCRBoundingBox(x=20, y=70, width=140, height=22),
        ),
        OCRItem(
            text="Mfd. by MetriGuard Food Products Pvt Ltd, Mumbai 400001",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=20, y=110, width=340, height=24),
        ),
        OCRItem(
            text="Mfg. Date: 10/2025",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=20, y=150, width=180, height=22),
        ),
        OCRItem(
            text="Consumer Care: 1800-111-222 care@metriguard.com",
            confidence=0.91,
            bounding_box=OCRBoundingBox(x=20, y=190, width=290, height=22),
        ),
        OCRItem(
            text="USP Rs. 0.30 / g",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=20, y=230, width=160, height=22),
        ),
    ]

    mock_provider = MockOCRProvider(custom_items=compliant_items)
    custom_ocr = OCRService(provider=mock_provider)
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=custom_ocr
    )

    # 1. Create inspection session
    create_res = client.post("/api/v1/inspections", json={"product_name": "Premium Tea 500g", "notes": "E2E Test"})
    assert create_res.status_code == 201
    inspection_id = create_res.json()["id"]

    # 2. Upload image
    img_bytes = make_test_image(format="JPEG")
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("label.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    assert upload_data["status"] == "COMPLIANT"
    assert upload_data["confidence_score"] >= 0.80
    assert len(upload_data["violations"]) == 0
    assert "image_url" in upload_data

    # 3. Retrieve inspection and verify persistence
    get_res = client.get(f"/api/v1/inspections/{inspection_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["status"] == "COMPLIANT"
    assert len(details["violations"]) == 0
    assert len(details["declarations"]) >= 5
    assert details["result"]["final_status"] == "COMPLIANT"


# =========================================================================
# Scenario 2: Non-Compliant Inspection
# =========================================================================
def test_e2e_non_compliant_inspection():
    """
    User uploads a package image missing mandatory retail declarations (e.g., missing MRP).
    System produces NON_COMPLIANT and stores violations with rule ID, version, and evidence.
    """
    non_compliant_items = [
        OCRItem(
            text="Net Wt: 500g",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=20, y=70, width=140, height=22),
        ),
        OCRItem(
            text="Mfd. by ABC Industries Pvt Ltd",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=20, y=110, width=300, height=24),
        ),
        OCRItem(
            text="Mfg: 05/2025",
            confidence=0.90,
            bounding_box=OCRBoundingBox(x=20, y=150, width=150, height=20),
        ),
    ]

    mock_provider = MockOCRProvider(custom_items=non_compliant_items)
    custom_ocr = OCRService(provider=mock_provider)
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=custom_ocr
    )

    # 1. Create inspection session
    create_res = client.post("/api/v1/inspections", json={"product_name": "Biscuits 500g"})
    assert create_res.status_code == 201
    inspection_id = create_res.json()["id"]

    # 2. Upload image
    img_bytes = make_test_image(format="JPEG")
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("pack.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    assert upload_data["status"] == "NON_COMPLIANT"
    assert len(upload_data["violations"]) > 0

    # 3. Verify violation fields in database record
    get_res = client.get(f"/api/v1/inspections/{inspection_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["status"] == "NON_COMPLIANT"
    assert len(details["violations"]) > 0

    mrp_violation = next((v for v in details["violations"] if "R06-1-E" in v["rule_id"]), None)
    assert mrp_violation is not None
    assert mrp_violation["rule_id"] == "LMR-2011-R06-1-E"
    assert mrp_violation["rule_version"] == "1.0.0"
    assert "missing" in mrp_violation["explanation"].lower()
    assert mrp_violation["severity"] == "CRITICAL"


# =========================================================================
# Scenario 3: Manual-Review Inspection
# =========================================================================
def test_e2e_manual_review_inspection():
    """
    Package contains ambiguous declarations (e.g. conflicting MRPs) or low-confidence values.
    System evaluates to MANUAL_REVIEW and produces explanatory warnings.
    """
    ambiguous_items = [
        OCRItem(
            text="MRP Rs. 150.00 (Incl. of all taxes)",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=20, y=30, width=280, height=25),
        ),
        OCRItem(
            text="MRP Rs. 200.00",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=20, y=60, width=200, height=25),
        ),
        OCRItem(
            text="Net Wt: 500g",
            confidence=0.96,
            bounding_box=OCRBoundingBox(x=20, y=90, width=140, height=22),
        ),
        OCRItem(
            text="Mfd. by MetriGuard Food Products Pvt Ltd",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=20, y=120, width=340, height=24),
        ),
        OCRItem(
            text="Mfg. Date: 10/2025",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=20, y=150, width=180, height=22),
        ),
        OCRItem(
            text="Consumer Care: 1800-111-222 care@metriguard.com",
            confidence=0.91,
            bounding_box=OCRBoundingBox(x=20, y=180, width=280, height=22),
        ),
        OCRItem(
            text="USP Rs. 0.30 / g",
            confidence=0.93,
            bounding_box=OCRBoundingBox(x=20, y=210, width=150, height=22),
        ),
    ]

    mock_provider = MockOCRProvider(custom_items=ambiguous_items)
    custom_ocr = OCRService(provider=mock_provider)
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=custom_ocr
    )

    create_res = client.post("/api/v1/inspections", json={"product_name": "Ambiguous Pack"})
    inspection_id = create_res.json()["id"]

    img_bytes = make_test_image(format="JPEG")
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("pack.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["status"] == "MANUAL_REVIEW"

    # Verify manual review status in persisted inspection
    get_res = client.get(f"/api/v1/inspections/{inspection_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["status"] == "MANUAL_REVIEW"
    assert "review" in details["result"]["summary"].lower()


# =========================================================================
# Scenario 4: Invalid Upload
# =========================================================================
def test_e2e_invalid_upload():
    """
    User attempts to upload a non-image text file or corrupted payload.
    Backend rejects with HTTP 400 without corrupting the inspection session.
    """
    create_res = client.post("/api/v1/inspections", json={"product_name": "Validation Target"})
    inspection_id = create_res.json()["id"]

    # 1. Non-image text file
    fake_txt = b"This is plain text pretending to be an image."
    res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("notes.txt", fake_txt, "text/plain")}
    )
    assert res.status_code in (400, 415)
    detail_msg = res.json()["detail"].lower()
    assert "image" in detail_msg or "extension" in detail_msg or "file" in detail_msg

    # 2. Corrupted file with image/jpeg MIME
    res_corrupt = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("corrupt.jpg", b"\x00\x01\x02\x03\x04", "image/jpeg")}
    )
    assert res_corrupt.status_code == 400

    # 3. Verify inspection remains unaffected in CREATED status
    check_res = client.get(f"/api/v1/inspections/{inspection_id}")
    assert check_res.status_code == 200
    assert check_res.json()["status"] == "CREATED"
    assert len(check_res.json()["images"]) == 0


# =========================================================================
# Scenario 5: OCR Failure
# =========================================================================
def test_e2e_ocr_failure():
    """
    OCR provider crashes or raises a runtime error.
    CRITICAL RULE: OCR failure MUST NOT become COMPLIANT.
    It must route gracefully to MANUAL_REVIEW.
    """
    failing_provider = MockOCRProvider(simulate_failure=True, failure_message="OCR engine crashed.")
    custom_ocr = OCRService(provider=failing_provider)
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=custom_ocr
    )

    create_res = client.post("/api/v1/inspections", json={"product_name": "OCR Crash Test"})
    inspection_id = create_res.json()["id"]

    img_bytes = make_test_image(format="JPEG")
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("crash.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()

    # CRITICAL: OCR failure must NOT be COMPLIANT
    assert upload_data["status"] != "COMPLIANT"
    assert upload_data["status"] == "MANUAL_REVIEW"
    assert upload_data["confidence_score"] == 0.0

    # Verify persisted state
    get_res = client.get(f"/api/v1/inspections/{inspection_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["status"] == "MANUAL_REVIEW"
    assert "ocr processing failed" in details["result"]["summary"].lower()


# =========================================================================
# Scenario 6: Rule-Engine Failure
# =========================================================================
def test_e2e_rule_engine_failure():
    """
    Rule engine throws an unexpected exception during evaluation.
    System gracefully catches the error and marks session as MANUAL_REVIEW (never COMPLIANT).
    """
    class BrokenRuleEngine(RuleEngine):
        def evaluate_extraction(self, *args, **kwargs):
            raise RuntimeError("Unexpected failure in regulatory rule evaluator.")

    custom_ocr = OCRService(provider=MockOCRProvider())
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=custom_ocr,
        rule_engine=BrokenRuleEngine()
    )

    create_res = client.post("/api/v1/inspections", json={"product_name": "Engine Crash Test"})
    inspection_id = create_res.json()["id"]

    img_bytes = make_test_image(format="JPEG")
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("sample.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()

    assert upload_data["status"] != "COMPLIANT"
    assert upload_data["status"] == "MANUAL_REVIEW"

    # Verify persisted result reflects rule engine failure
    get_res = client.get(f"/api/v1/inspections/{inspection_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["status"] == "MANUAL_REVIEW"
    assert "rule engine evaluation failed" in details["result"]["summary"].lower()


# =========================================================================
# Scenario 7: Missing Image
# =========================================================================
def test_e2e_missing_image():
    """
    User requests an image file that does not exist or whose storage file is missing.
    Returns HTTP 404 with clear detail message.
    """
    create_res = client.post("/api/v1/inspections", json={"product_name": "Missing Image Test"})
    inspection_id = create_res.json()["id"]

    # 1. Non-existent image ID
    res_no_image = client.get(f"/api/v1/inspections/{inspection_id}/images/99999/file")
    assert res_no_image.status_code == 404
    assert "not found" in res_no_image.json()["detail"].lower()

    # 2. Non-existent inspection ID
    res_no_insp = client.get("/api/v1/inspections/88888/images/1/file")
    assert res_no_insp.status_code == 404
    assert "not found" in res_no_insp.json()["detail"].lower()

    # 3. Image record exists in DB, but storage file has been deleted
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=OCRService(provider=MockOCRProvider())
    )
    img_bytes = make_test_image(format="JPEG")
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("to_delete.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201
    image_id = upload_res.json()["id"]
    file_path_key = upload_res.json()["file_path"]

    # Delete file from storage
    storage = get_storage_service()
    local_path = storage.get_file_path(file_path_key)
    if local_path and Path(local_path).exists():
        Path(local_path).unlink()

    # Retrieve missing file -> 404
    missing_res = client.get(f"/api/v1/inspections/{inspection_id}/images/{image_id}/file")
    assert missing_res.status_code == 404
    assert "not found" in missing_res.json()["detail"].lower()


# =========================================================================
# Scenario 8: Empty Database / Non-Existent Inspection
# =========================================================================
def test_e2e_empty_database():
    """
    Querying inspection sessions with non-existent IDs returns HTTP 404.
    Listing inspections returns a valid list without crashing.
    """
    res = client.get("/api/v1/inspections/999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    list_res = client.get("/api/v1/inspections")
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)


# =========================================================================
# Scenario 9: Repeated Inspection Retrieval
# =========================================================================
def test_e2e_repeated_inspection_retrieval():
    """
    Retrieving an inspection session multiple times yields consistent, idempotent results
    without data drift, duplication of violations, or changing confidence values.
    """
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=OCRService(provider=MockOCRProvider())
    )

    create_res = client.post("/api/v1/inspections", json={"product_name": "Idempotent Check"})
    inspection_id = create_res.json()["id"]

    img_bytes = make_test_image(format="JPEG")
    upload_res = client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files={"file": ("item.jpg", img_bytes, "image/jpeg")}
    )
    assert upload_res.status_code == 201

    # Retrieve 3 consecutive times
    res1 = client.get(f"/api/v1/inspections/{inspection_id}").json()
    res2 = client.get(f"/api/v1/inspections/{inspection_id}").json()
    res3 = client.get(f"/api/v1/inspections/{inspection_id}").json()

    assert res1["status"] == res2["status"] == res3["status"]
    assert res1["overall_confidence"] == res2["overall_confidence"] == res3["overall_confidence"]
    assert len(res1["declarations"]) == len(res2["declarations"]) == len(res3["declarations"])
    assert len(res1["violations"]) == len(res2["violations"]) == len(res3["violations"])
    assert len(res1["images"]) == len(res2["images"]) == len(res3["images"])
    assert res1["result"]["final_status"] == res2["result"]["final_status"] == res3["result"]["final_status"]
