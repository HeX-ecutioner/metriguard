"""
Tests for PDF Report Generation in AlgoForge Prototype - MK I.

Validates:
1. Successful PDF generation for COMPLIANT inspections.
2. Successful PDF generation for NON_COMPLIANT inspections with findings & evidence.
3. Successful PDF generation for MANUAL_REVIEW and FAILED inspections.
4. Correct inspection ID, outcome, declarations, findings, and disclaimer in generated PDF text.
5. Missing optional fields (null product name, null notes, null confidence, null bounding box) handled gracefully.
6. Rejection of non-existent inspection IDs (HTTP 404).
7. Rejection of incomplete inspections in CREATED and PROCESSING states (HTTP 409).
8. Immutability: generating reports never alters database records or creates new records.
9. Verification of report disposition headers (inline vs attachment download).
"""

import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app
from app.db.database import get_db, Base
from app.db.models import (
    Inspection,
    InspectionStatus,
    PackageImage,
    Declaration,
    Violation,
    ViolationSeverity,
    InspectionResult,
)


from app.db.database import SessionLocal, get_db


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def extract_normalized_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return " ".join(" ".join(page.extract_text().split()) for page in reader.pages)


def test_pdf_generation_compliant_inspection(client, db_session):
    """
    Test generating a PDF report for a COMPLIANT inspection.
    Validates that pypdf can extract the text and that all key elements match.
    """
    inspection = Inspection(
        status=InspectionStatus.COMPLIANT,
        product_name="Certified Basmati Rice 5kg",
        overall_confidence=0.965,
        notes="High quality scan.",
        created_at=datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    # Add Declarations
    decl_mrp = Declaration(
        inspection_id=inspection.id,
        declaration_type="MRP",
        extracted_value="Rs. 450.00 (incl. of all taxes)",
        confidence=0.98,
        bounding_box='{"x": 100, "y": 200, "width": 150, "height": 40}',
    )
    decl_net_qty = Declaration(
        inspection_id=inspection.id,
        declaration_type="NET_QUANTITY",
        extracted_value="5 kg",
        confidence=0.95,
        bounding_box='{"x": 100, "y": 300, "width": 80, "height": 30}',
    )
    result = InspectionResult(
        inspection_id=inspection.id,
        final_status=InspectionStatus.COMPLIANT,
        summary="All mandatory Legal Metrology declarations are present and compliant.",
    )
    db_session.add_all([decl_mrp, decl_net_qty, result])
    db_session.commit()

    # Request PDF report
    response = client.get(f"/api/v1/inspections/{inspection.id}/report")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert f'filename="inspection_{inspection.id}_report.pdf"' in response.headers["content-disposition"]
    assert response.headers["content-disposition"].startswith("inline")

    full_text = extract_normalized_pdf_text(response.content)

    # Assert content matches saved inspection
    assert "AlgoForge Prototype" in full_text
    assert f"Inspection #{inspection.id}" in full_text
    assert "Certified Basmati Rice 5kg" in full_text
    assert "COMPLIANT" in full_text
    assert "96.5%" in full_text
    assert "Rs. 450.00" in full_text
    assert "5 kg" in full_text
    assert "STATUTORY PROTOTYPE DISCLAIMER" in full_text
    assert "Not for Legal Certification" in full_text


def test_pdf_generation_non_compliant_inspection_with_violations(client, db_session):
    """
    Test generating a PDF report for a NON_COMPLIANT inspection.
    Validates that Rule IDs, versions, explanations, and evidence appear in the PDF.
    """
    inspection = Inspection(
        status=InspectionStatus.NON_COMPLIANT,
        product_name="Snack Bites 200g",
        overall_confidence=0.89,
        created_at=datetime(2026, 9, 8, 11, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    # Add Violation
    violation = Violation(
        inspection_id=inspection.id,
        rule_id="LMR-2011-R06-1-E",
        rule_version="2011",
        title="Mandatory MRP Declaration Missing",
        explanation="The Maximum Retail Price (MRP) declaration is absent from the principal display panel.",
        severity=ViolationSeverity.CRITICAL,
        confidence=0.92,
        expected_value="MRP Rs. XX.XX incl. of all taxes",
        measured_value="Missing",
        evidence_bounding_box=None,
    )
    result = InspectionResult(
        inspection_id=inspection.id,
        final_status=InspectionStatus.NON_COMPLIANT,
        summary="1 statutory non-compliance violation detected under Rule 6(1)(e).",
    )
    db_session.add_all([violation, result])
    db_session.commit()

    # Request PDF report with download=true
    response = client.get(f"/api/v1/inspections/{inspection.id}/report?download=true")
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment")

    full_text = extract_normalized_pdf_text(response.content)

    assert "NON COMPLIANT" in full_text or "NON_COMPLIANT" in full_text
    assert "LMR-2011-R06-1-E" in full_text
    assert "v2011" in full_text
    assert "CRITICAL" in full_text
    assert "Mandatory MRP Declaration Missing" in full_text
    assert "Declaration Absent / Not Visible" in full_text


def test_pdf_generation_manual_review_inspection(client, db_session):
    """
    Test generating a PDF report for a MANUAL_REVIEW inspection.
    Validates that Safe AI uncertainty routing is preserved distinctly.
    """
    inspection = Inspection(
        status=InspectionStatus.MANUAL_REVIEW,
        product_name=None,
        overall_confidence=0.45,
        created_at=datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    result = InspectionResult(
        inspection_id=inspection.id,
        final_status=InspectionStatus.MANUAL_REVIEW,
        summary="Automated OCR confidence is insufficient (45%). Routed to MANUAL_REVIEW to prevent false statutory violations.",
    )
    db_session.add(result)
    db_session.commit()

    response = client.get(f"/api/v1/inspections/{inspection.id}/report")
    assert response.status_code == 200

    full_text = extract_normalized_pdf_text(response.content)

    assert "MANUAL REVIEW" in full_text or "MANUAL_REVIEW" in full_text
    assert "prevent false statutory violations" in full_text
    assert "45.0%" in full_text


def test_pdf_generation_failed_inspection(client, db_session):
    """
    Test generating a PDF report for a FAILED inspection.
    Validates distinct pipeline failure presentation.
    """
    inspection = Inspection(
        status=InspectionStatus.FAILED,
        product_name="Faulty Upload",
        overall_confidence=None,
        created_at=datetime(2026, 9, 8, 13, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    result = InspectionResult(
        inspection_id=inspection.id,
        final_status=InspectionStatus.FAILED,
        summary="Storage system write failure occurred during processing.",
    )
    db_session.add(result)
    db_session.commit()

    response = client.get(f"/api/v1/inspections/{inspection.id}/report")
    assert response.status_code == 200

    full_text = extract_normalized_pdf_text(response.content)

    assert "FAILED" in full_text
    assert "Inspection Processing Failure" in full_text
    assert "Storage system write failure" in full_text


def test_pdf_generation_missing_optional_fields(client, db_session):
    """
    Test generating a PDF report when optional fields are null.
    Validates that null product_name, notes, confidence, and bounding boxes do not cause crashes or invent data.
    """
    inspection = Inspection(
        status=InspectionStatus.COMPLIANT,
        product_name=None,
        overall_confidence=None,
        notes=None,
        created_at=datetime(2026, 9, 8, 14, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    # Empty declarations and violations
    result = InspectionResult(
        inspection_id=inspection.id,
        final_status=InspectionStatus.COMPLIANT,
        summary="No issues found.",
    )
    db_session.add(result)
    db_session.commit()

    response = client.get(f"/api/v1/inspections/{inspection.id}/report")
    assert response.status_code == 200

    full_text = extract_normalized_pdf_text(response.content)

    assert "Unspecified Commodity" in full_text
    assert "COMPLIANT" in full_text


def test_pdf_generation_rejects_non_existent_inspection(client):
    """
    Test requesting a PDF report for an inspection ID that does not exist returns HTTP 404.
    """
    response = client.get("/api/v1/inspections/999999/report")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_pdf_generation_rejects_incomplete_inspection_created(client, db_session):
    """
    Test requesting a PDF report for an inspection in CREATED status returns HTTP 409.
    """
    inspection = Inspection(
        status=InspectionStatus.CREATED,
        product_name="Pending Inspection",
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    response = client.get(f"/api/v1/inspections/{inspection.id}/report")
    assert response.status_code == 409
    data = response.json()
    assert "cannot generate a report" in data["detail"].lower() or "not completed" in data["detail"].lower()


def test_pdf_generation_rejects_incomplete_inspection_processing(client, db_session):
    """
    Test requesting a PDF report for an inspection in PROCESSING status returns HTTP 409.
    """
    inspection = Inspection(
        status=InspectionStatus.PROCESSING,
        product_name="In-Flight Inspection",
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    response = client.get(f"/api/v1/inspections/{inspection.id}/report")
    assert response.status_code == 409
    data = response.json()
    assert "cannot generate a report" in data["detail"].lower() or "not completed" in data["detail"].lower()


def test_pdf_generation_is_strictly_immutable(client, db_session):
    """
    Test that generating a PDF report does not alter database row counts,
    does not create new inspections, and does not mutate any fields.
    """
    inspection = Inspection(
        status=InspectionStatus.COMPLIANT,
        product_name="Immutable Product",
        overall_confidence=0.99,
        created_at=datetime(2026, 9, 8, 15, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    result = InspectionResult(
        inspection_id=inspection.id,
        final_status=InspectionStatus.COMPLIANT,
        summary="Compliant package.",
    )
    db_session.add(result)
    db_session.commit()

    # Pre-generation counts and field snapshot
    pre_inspection_count = db_session.query(Inspection).count()
    pre_result_count = db_session.query(InspectionResult).count()
    pre_updated_at = inspection.updated_at
    pre_status = inspection.status

    # Request report 3 times consecutively
    for _ in range(3):
        res = client.get(f"/api/v1/inspections/{inspection.id}/report")
        assert res.status_code == 200

    # Post-generation assertions
    post_inspection_count = db_session.query(Inspection).count()
    post_result_count = db_session.query(InspectionResult).count()
    db_session.refresh(inspection)

    assert post_inspection_count == pre_inspection_count
    assert post_result_count == pre_result_count
    assert inspection.status == pre_status
    assert inspection.updated_at == pre_updated_at


def test_pdf_generation_with_embedded_image(client, db_session):
    """
    Test generating a PDF report for an inspection with an attached package image.
    Validates that the image is read, embedded, and metadata is displayed.
    """
    from PIL import Image as PILImage
    from app.services.storage import get_storage_service

    inspection = Inspection(
        status=InspectionStatus.COMPLIANT,
        product_name="Product with Embedded Image",
        overall_confidence=0.97,
        created_at=datetime(2026, 9, 8, 16, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)

    storage = get_storage_service()
    img_buf = io.BytesIO()
    pil_img = PILImage.new("RGB", (200, 150), color=(50, 120, 200))
    pil_img.save(img_buf, format="JPEG")
    img_bytes = img_buf.getvalue()

    rel_path = f"uploads/test_{inspection.id}_embedded.jpg"
    full_path = storage.base_dir / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(img_bytes)

    pkg_img = PackageImage(
        inspection_id=inspection.id,
        file_path=rel_path,
        original_filename="sample_label.jpg",
        mime_type="image/jpeg",
        file_size=len(img_bytes),
        width=200,
        height=150,
    )
    result = InspectionResult(
        inspection_id=inspection.id,
        final_status=InspectionStatus.COMPLIANT,
        summary="Image embedded successfully.",
    )
    db_session.add_all([pkg_img, result])
    db_session.commit()

    res = client.get(f"/api/v1/inspections/{inspection.id}/report")
    assert res.status_code == 200
    assert len(res.content) > 5000

    full_text = extract_normalized_pdf_text(res.content)
    assert "sample_label.jpg" in full_text
    assert "200 × 150 px" in full_text
    assert "Product with Embedded Image" in full_text
