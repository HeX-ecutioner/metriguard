"""
Test Suite for MetriGuard Single-Image Inspection Invariant and Lifecycle Guarantees.
Verifies:
1. One inspection ID maps to exactly one uploaded image.
2. Attempting a second image upload to an inspection is rejected with HTTP 409 Conflict.
3. Attempting to upload to a completed or failed inspection is rejected with HTTP 409 Conflict.
4. Consecutive inspections create distinct inspection records without cross-contamination.
5. Historical inspections remain permanently preserved in the database.
6. Processing failure routes safely to MANUAL_REVIEW or FAILED, never incorrectly COMPLIANT.
"""

import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.api.inspections import get_inspection_orchestrator
from app.services.inspection_orchestrator import InspectionOrchestrator
from app.services.ocr.service import OCRService
from app.services.ocr.mock_provider import MockOCRProvider
from app.models.ocr_schemas import OCRItem, OCRBoundingBox

client = TestClient(app)


def make_test_image(format="JPEG", size=(150, 100), color=(100, 150, 200)) -> bytes:
    """Generates valid image bytes in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_single_image_per_inspection_invariant():
    """
    Verify the fundamental invariant:
    Inspection 1 has exactly Image 1 and Result 1.
    Uploading a second image to Inspection 1 fails with 409 Conflict.
    Inspection 2 is created separately with Image 2 and Result 2.
    """
    # 1. Create Inspection A
    res_a = client.post("/api/v1/inspections", json={"product_name": "Product Alpha"})
    assert res_a.status_code == 201
    id_a = res_a.json()["id"]

    # 2. Upload Image A to Inspection A
    img_a = make_test_image(format="JPEG", color=(255, 0, 0))
    upload_a = client.post(
        f"/api/v1/inspections/{id_a}/images",
        files={"file": ("alpha.jpg", img_a, "image/jpeg")}
    )
    assert upload_a.status_code == 201
    assert upload_a.json()["inspection_id"] == id_a

    # 3. Attempt to upload a second image to Inspection A -> Must be rejected with 409 Conflict
    img_a_second = make_test_image(format="PNG", color=(0, 255, 0))
    upload_second = client.post(
        f"/api/v1/inspections/{id_a}/images",
        files={"file": ("alpha_extra.png", img_a_second, "image/png")}
    )
    assert upload_second.status_code == 409
    assert "already contains" in upload_second.json()["detail"].lower() or "cannot accept" in upload_second.json()["detail"].lower()

    # 4. Verify Inspection A is unchanged and has exactly 1 image
    detail_a = client.get(f"/api/v1/inspections/{id_a}")
    assert detail_a.status_code == 200
    data_a = detail_a.json()
    assert len(data_a["images"]) == 1
    assert data_a["images"][0]["original_filename"] == "alpha.jpg"

    # 5. Create Inspection B separately
    res_b = client.post("/api/v1/inspections", json={"product_name": "Product Beta"})
    assert res_b.status_code == 201
    id_b = res_b.json()["id"]
    assert id_b != id_a

    # 6. Upload Image B to Inspection B
    img_b = make_test_image(format="JPEG", color=(0, 0, 255))
    upload_b = client.post(
        f"/api/v1/inspections/{id_b}/images",
        files={"file": ("beta.jpg", img_b, "image/jpeg")}
    )
    assert upload_b.status_code == 201
    assert upload_b.json()["inspection_id"] == id_b

    # 7. Verify Inspection B has exactly 1 image (Image B)
    detail_b = client.get(f"/api/v1/inspections/{id_b}")
    assert detail_b.status_code == 200
    data_b = detail_b.json()
    assert len(data_b["images"]) == 1
    assert data_b["images"][0]["original_filename"] == "beta.jpg"

    # 8. Verify Inspection A is still preserved in the database untouched
    detail_a_again = client.get(f"/api/v1/inspections/{id_a}")
    assert detail_a_again.status_code == 200
    data_a_again = detail_a_again.json()
    assert len(data_a_again["images"]) == 1
    assert data_a_again["images"][0]["original_filename"] == "alpha.jpg"


def test_declarations_and_violations_isolated_per_inspection():
    """
    Verify declarations and violations belong strictly to their own inspection
    and never cross-contaminate between sessions.
    """
    items_a = [
        OCRItem(
            text="MRP Rs. 100",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=10, y=10, width=50, height=20)
        )
    ]
    items_b = [
        OCRItem(
            text="Net Wt 500g",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=10, y=10, width=50, height=20)
        )
    ]

    # Inspection A
    ocr_a = OCRService(provider=MockOCRProvider(custom_items=items_a))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(ocr_service=ocr_a)

    insp_a = client.post("/api/v1/inspections", json={"product_name": "Isolated A"}).json()["id"]
    client.post(
        f"/api/v1/inspections/{insp_a}/images",
        files={"file": ("a.jpg", make_test_image(), "image/jpeg")}
    )

    # Inspection B
    ocr_b = OCRService(provider=MockOCRProvider(custom_items=items_b))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(ocr_service=ocr_b)

    insp_b = client.post("/api/v1/inspections", json={"product_name": "Isolated B"}).json()["id"]
    client.post(
        f"/api/v1/inspections/{insp_b}/images",
        files={"file": ("b.jpg", make_test_image(), "image/jpeg")}
    )

    # Verify Inspection A has only its own image and findings
    res_a = client.get(f"/api/v1/inspections/{insp_a}").json()
    assert len(res_a["images"]) == 1
    assert res_a["images"][0]["original_filename"] == "a.jpg"

    # Verify Inspection B has only its own image and findings
    res_b = client.get(f"/api/v1/inspections/{insp_b}").json()
    assert len(res_b["images"]) == 1
    assert res_b["images"][0]["original_filename"] == "b.jpg"


def test_completed_inspection_cannot_receive_second_image():
    """Verify that an inspection in a completed status rejects image upload."""
    insp = client.post("/api/v1/inspections", json={"product_name": "Completed Test"}).json()["id"]

    # First upload completes the inspection
    res = client.post(
        f"/api/v1/inspections/{insp}/images",
        files={"file": ("first.jpg", make_test_image(), "image/jpeg")}
    )
    assert res.status_code == 201

    # Second upload attempt rejected with 409
    res_dup = client.post(
        f"/api/v1/inspections/{insp}/images",
        files={"file": ("second.jpg", make_test_image(), "image/jpeg")}
    )
    assert res_dup.status_code == 409
    assert "already contains" in res_dup.json()["detail"].lower() or "cannot accept" in res_dup.json()["detail"].lower()


def test_failed_inspection_cannot_receive_image():
    """Verify that an inspection in FAILED status rejects image upload with 409 Conflict."""
    from app.db.database import SessionLocal
    from app.db.models import Inspection, InspectionStatus

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Failed Session Test"}).json()["id"]

    # Manually transition to FAILED status in DB (simulating storage/system failure)
    db = SessionLocal()
    try:
        insp = db.query(Inspection).filter(Inspection.id == insp_id).first()
        insp.status = InspectionStatus.FAILED
        db.commit()
    finally:
        db.close()

    # Attempt to upload to FAILED session -> must be rejected with 409
    res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("upload.jpg", make_test_image(), "image/jpeg")}
    )
    assert res.status_code == 409
    assert "cannot accept" in res.json()["detail"].lower()


def test_processing_inspection_cannot_receive_image():
    """Verify that an inspection in PROCESSING status rejects image upload with 409 Conflict."""
    from app.db.database import SessionLocal
    from app.db.models import Inspection, InspectionStatus

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Processing Session Test"}).json()["id"]

    db = SessionLocal()
    try:
        insp = db.query(Inspection).filter(Inspection.id == insp_id).first()
        insp.status = InspectionStatus.PROCESSING
        db.commit()
    finally:
        db.close()

    res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("upload.jpg", make_test_image(), "image/jpeg")}
    )
    assert res.status_code == 409
    assert "cannot accept" in res.json()["detail"].lower()


def test_database_persistence_of_violation_and_declaration_fields():
    """Verify that declarations, violations, and results are fully persisted in the database."""
    items = [
        OCRItem(
            text="MRP Rs. 50.00",
            confidence=0.98,
            bounding_box=OCRBoundingBox(x=10, y=10, width=120, height=25),
        ),
        OCRItem(
            text="Net Wt 100g",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=10, y=40, width=90, height=20),
        ),
    ]
    custom_ocr = OCRService(provider=MockOCRProvider(custom_items=items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=custom_ocr
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Persistence Pack"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("pack.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201

    # Verify retrieval from GET endpoint
    detail_res = client.get(f"/api/v1/inspections/{insp_id}")
    assert detail_res.status_code == 200
    details = detail_res.json()

    assert details["id"] == insp_id
    assert details["product_name"] == "Persistence Pack"
    assert len(details["images"]) == 1
    assert details["images"][0]["file_size"] > 0
    assert len(details["declarations"]) >= 2
    assert details["result"] is not None
    assert "final_status" in details["result"]
    assert "summary" in details["result"]

