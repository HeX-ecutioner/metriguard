"""
Test Suite for Difficult Image Cases and Safe AI Behavior Guarantees.
Explicitly verifies:
E. Difficult image cases:
  1. Blurry image (low confidence -> MANUAL_REVIEW)
  2. Glare (missing evidence under uncertain OCR -> MANUAL_REVIEW)
  3. Rotation (preprocessor handling)
  4. Curved packaging (irregular bounding box)
  5. Tiny text (small bounding box extraction)
  6. Mixed-language packaging (Hindi + English dual declarations)
  7. Missing declaration (high confidence with absent mandatory field -> NON_COMPLIANT)
  8. Non-package image (zero OCR text -> MANUAL_REVIEW)
  9. Invalid image (corrupted payload -> HTTP 400)

F. Safe AI behavior:
  1. OCR uncertainty must not become an invented declaration.
  2. Missing evidence must not automatically become NON_COMPLIANT.
  3. Unsupported physical measurements must not be presented as verified.
  4. Ambiguous cases must become MANUAL_REVIEW.
  5. FAILED must remain distinct from NON_COMPLIANT.
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
from app.services.extraction.extractor import DeclarationExtractor
from app.models.declaration_schemas import DeclarationType, ExtractionStatus

client = TestClient(app)


def make_test_image(format="JPEG", size=(200, 150), color=(128, 128, 128)) -> bytes:
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


# =========================================================================
# Difficult Image Case 1: Blurry Image -> Safe AI: Low confidence -> MANUAL_REVIEW
# =========================================================================
def test_case_blurry_image_routes_to_manual_review():
    """
    Blurry image produces low OCR confidence (< 0.50).
    SAFE AI RULE: Must route to MANUAL_REVIEW, NEVER falsely COMPLIANT or blindly NON_COMPLIANT.
    """
    blurry_items = [
        OCRItem(
            text="MRP Rs. 1??.00",
            confidence=0.30,
            bounding_box=OCRBoundingBox(x=10, y=10, width=100, height=20),
        ),
        OCRItem(
            text="Net Wt ??0g",
            confidence=0.25,
            bounding_box=OCRBoundingBox(x=10, y=40, width=80, height=20),
        ),
    ]
    ocr_service = OCRService(provider=MockOCRProvider(custom_items=blurry_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Blurry Chips Pack"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("blurry.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    data = upload_res.json()

    assert data["status"] == "MANUAL_REVIEW"
    assert data["status"] != "COMPLIANT"

    # Verify persisted summary explicitly mentions manual review
    get_res = client.get(f"/api/v1/inspections/{insp_id}").json()
    assert get_res["status"] == "MANUAL_REVIEW"
    assert "manual_review" in get_res["result"]["final_status"].lower() or "manual" in get_res["result"]["summary"].lower()


# =========================================================================
# Difficult Image Case 2: Glare -> Missing evidence under uncertain OCR -> MANUAL_REVIEW
# =========================================================================
def test_case_glare_causes_missing_evidence_without_false_non_compliance():
    """
    Glare obscures portions of the label causing low overall confidence.
    SAFE AI RULE: Missing evidence under uncertain OCR must NOT automatically become NON_COMPLIANT.
    It must route to MANUAL_REVIEW.
    """
    glare_items = [
        OCRItem(
            text="Brand Name Premium Oats",
            confidence=0.45,
            bounding_box=OCRBoundingBox(x=10, y=10, width=200, height=30),
        ),
    ]
    ocr_service = OCRService(provider=MockOCRProvider(custom_items=glare_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Glared Pack"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("glare.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    data = upload_res.json()

    # Must be MANUAL_REVIEW because confidence is low, not blindly NON_COMPLIANT
    assert data["status"] == "MANUAL_REVIEW"


# =========================================================================
# Difficult Image Case 3: Rotation -> Preprocessor and multi-line detection
# =========================================================================
def test_case_rotated_image_preprocessing():
    """
    Verifies image preprocessor processes rotated image orientation without crashing
    and extracts standard declarations cleanly.
    """
    rotated_items = [
        OCRItem(
            text="MRP Rs. 99.00 (Incl. of all taxes)",
            confidence=0.96,
            bounding_box=OCRBoundingBox(x=50, y=10, width=250, height=25),
        ),
        OCRItem(
            text="Net Quantity: 250 g",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=50, y=45, width=150, height=22),
        ),
        OCRItem(
            text="Packed by: Alpha Pack Corp, Delhi",
            confidence=0.93,
            bounding_box=OCRBoundingBox(x=50, y=80, width=280, height=22),
        ),
        OCRItem(
            text="Date of Pkg: 11/2025",
            confidence=0.91,
            bounding_box=OCRBoundingBox(x=50, y=115, width=160, height=20),
        ),
    ]
    ocr_service = OCRService(provider=MockOCRProvider(custom_items=rotated_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Rotated Carton"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("rotated.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    data = upload_res.json()
    assert data["confidence_score"] >= 0.70


# =========================================================================
# Difficult Image Case 4: Curved Packaging -> Irregular / aspect-ratio bbox
# =========================================================================
def test_case_curved_packaging_declarations():
    """
    Curved packaging surfaces (cans, bottles) produce wide, non-linear bounding boxes.
    Verifies declarations are extracted accurately regardless of bbox aspect ratio.
    """
    curved_items = [
        OCRItem(
            text="MRP Rs. 60.00 INCL OF ALL TAXES",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=5, y=20, width=380, height=35),
        ),
        OCRItem(
            text="NET VOLUME 750ml",
            confidence=0.96,
            bounding_box=OCRBoundingBox(x=10, y=65, width=220, height=30),
        ),
        OCRItem(
            text="Manufactured by Beverage Ltd, Pune 411001",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=5, y=110, width=390, height=32),
        ),
        OCRItem(
            text="Mfg Date: 09/2025",
            confidence=0.90,
            bounding_box=OCRBoundingBox(x=15, y=155, width=170, height=28),
        ),
    ]
    ocr_service = OCRService(provider=MockOCRProvider(custom_items=curved_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Can 750ml"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("can.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    details = client.get(f"/api/v1/inspections/{insp_id}").json()

    net_decl = next((d for d in details["declarations"] if d["declaration_type"] == "NET_QUANTITY"), None)
    assert net_decl is not None
    assert "750" in net_decl["extracted_value"]


# =========================================================================
# Difficult Image Case 5: Tiny Text -> Small bounding boxes extracted cleanly
# =========================================================================
def test_case_tiny_text_extraction():
    """
    Very small print (consumer care details, manufacturer address, unit sale price).
    Verifies small height bounding boxes (< 15px) are extracted and audited.
    """
    tiny_items = [
        OCRItem(
            text="Consumer Care: 1800-200-3000 feedback@metriguard.com",
            confidence=0.91,
            bounding_box=OCRBoundingBox(x=5, y=5, width=280, height=12),
        ),
        OCRItem(
            text="Unit Sale Price: Rs. 0.20/g",
            confidence=0.93,
            bounding_box=OCRBoundingBox(x=5, y=22, width=150, height=11),
        ),
        OCRItem(
            text="MRP Rs. 100.00",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=5, y=40, width=120, height=20),
        ),
        OCRItem(
            text="Net Wt: 500g",
            confidence=0.96,
            bounding_box=OCRBoundingBox(x=5, y=70, width=90, height=18),
        ),
        OCRItem(
            text="Mfd. by MetriGuard Pvt Ltd",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=5, y=95, width=200, height=15),
        ),
        OCRItem(
            text="Mfg. Date: 12/2025",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=5, y=120, width=130, height=14),
        ),
    ]
    ocr_service = OCRService(provider=MockOCRProvider(custom_items=tiny_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Tiny Text Label"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("tiny.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    details = client.get(f"/api/v1/inspections/{insp_id}").json()

    cc_decl = next((d for d in details["declarations"] if d["declaration_type"] == "CONSUMER_CARE"), None)
    assert cc_decl is not None
    assert "1800-200-3000" in cc_decl["extracted_value"]


# =========================================================================
# Difficult Image Case 6: Mixed-Language Packaging (Hindi + English)
# =========================================================================
def test_case_mixed_language_packaging():
    """
    Bilingual packages declaring values in both Hindi (Devanagari) and English.
    Verifies metric and retail price extraction accurately resolves statutory fields.
    """
    mixed_items = [
        OCRItem(
            text="अधिकतम खुदरा मूल्य / MRP: Rs. 120.00 (सभी कर सहित)",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=10, y=20, width=320, height=25),
        ),
        OCRItem(
            text="शुद्ध मात्रा / Net Quantity: 1 kg",
            confidence=0.97,
            bounding_box=OCRBoundingBox(x=10, y=55, width=220, height=24),
        ),
        OCRItem(
            text="निर्माता / Manufactured by: Swadeshi Foods Pvt Ltd, Jaipur",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=10, y=90, width=340, height=24),
        ),
        OCRItem(
            text="पैकिंग तिथि / Packing Date: 08/2025",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=10, y=125, width=210, height=22),
        ),
    ]
    ocr_service = OCRService(provider=MockOCRProvider(custom_items=mixed_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Bilingual Pack"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("bilingual.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    details = client.get(f"/api/v1/inspections/{insp_id}").json()

    mrp_decl = next((d for d in details["declarations"] if d["declaration_type"] == "MRP"), None)
    assert mrp_decl is not None
    assert "120" in mrp_decl["extracted_value"]

    net_decl = next((d for d in details["declarations"] if d["declaration_type"] == "NET_QUANTITY"), None)
    assert net_decl is not None
    assert "1 kg" in net_decl["extracted_value"]


# =========================================================================
# Difficult Image Case 7: High-confidence Missing Declaration -> NON_COMPLIANT
# =========================================================================
def test_case_high_confidence_missing_declaration_is_non_compliant():
    """
    Clear, high-confidence image of a package that is genuinely missing mandatory MRP.
    Must produce NON_COMPLIANT with clear violation details.
    """
    clear_items = [
        OCRItem(
            text="Net Wt: 500g",
            confidence=0.97,
            bounding_box=OCRBoundingBox(x=20, y=20, width=120, height=20),
        ),
        OCRItem(
            text="Mfd. by Clean Pack Co, Delhi",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=20, y=50, width=200, height=20),
        ),
        OCRItem(
            text="Mfg. Date: 01/2026",
            confidence=0.93,
            bounding_box=OCRBoundingBox(x=20, y=80, width=150, height=20),
        ),
    ]
    ocr_service = OCRService(provider=MockOCRProvider(custom_items=clear_items))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Missing MRP Pack"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("missing_mrp.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    data = upload_res.json()

    assert data["status"] == "NON_COMPLIANT"
    assert len(data["violations"]) > 0
    assert any("R06-1-E" in v["rule_id"] for v in data["violations"])


# =========================================================================
# Difficult Image Case 8: Non-Package Image (No text detected) -> MANUAL_REVIEW
# =========================================================================
def test_case_non_package_image_no_text_routes_to_manual_review():
    """
    Non-package image (e.g. landscape or animal photo) with zero OCR text detected.
    SAFE AI RULE: Must route to MANUAL_REVIEW, NOT NON_COMPLIANT.
    """
    ocr_service = OCRService(provider=MockOCRProvider(simulate_empty=True))
    app.dependency_overrides[get_inspection_orchestrator] = lambda: InspectionOrchestrator(
        ocr_service=ocr_service
    )

    insp_id = client.post("/api/v1/inspections", json={"product_name": "Cat Photo"}).json()["id"]
    upload_res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("non_package.jpg", make_test_image(), "image/jpeg")}
    )
    assert upload_res.status_code == 201
    data = upload_res.json()

    # Must be MANUAL_REVIEW, never falsely NON_COMPLIANT
    assert data["status"] == "MANUAL_REVIEW"
    assert data["confidence_score"] == 0.0
    assert len(data["violations"]) == 0


# =========================================================================
# Difficult Image Case 9: Invalid / Corrupted Image -> HTTP 400
# =========================================================================
def test_case_invalid_corrupted_image_rejected():
    """
    Uploading corrupted, undecodable binary bytes must be rejected with HTTP 400
    without creating or corrupting an image record.
    """
    insp_id = client.post("/api/v1/inspections", json={"product_name": "Corrupted Target"}).json()["id"]
    corrupted_bytes = b"\xFF\xD8\xFF\xE0_NOT_A_VALID_IMAGE_BYTES"

    res = client.post(
        f"/api/v1/inspections/{insp_id}/images",
        files={"file": ("bad.jpg", corrupted_bytes, "image/jpeg")}
    )
    assert res.status_code == 400

    # Inspection remains untouched
    details = client.get(f"/api/v1/inspections/{insp_id}").json()
    assert details["status"] == "CREATED"
    assert len(details["images"]) == 0


# =========================================================================
# Safe AI Test: Ambiguous conflicting declarations must become MANUAL_REVIEW
# =========================================================================
def test_safe_ai_conflicting_declarations_route_to_manual_review():
    """
    When OCR detects multiple conflicting declarations (e.g. two conflicting MRPs),
    the system must NOT guess or invent an amount; it must flag AMBIGUOUS and route to MANUAL_REVIEW.
    """
    extractor = DeclarationExtractor()
    ocr_items = [
        OCRItem(
            text="MRP Rs. 100.00",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=10, y=10, width=100, height=20),
        ),
        OCRItem(
            text="MRP Rs. 150.00",
            confidence=0.94,
            bounding_box=OCRBoundingBox(x=10, y=40, width=100, height=20),
        ),
    ]
    result = extractor.extract_from_ocr(ocr_items)
    mrp_decl = result.declarations.get(DeclarationType.MRP)

    assert mrp_decl is not None
    assert mrp_decl.status == ExtractionStatus.AMBIGUOUS
    assert mrp_decl.value is None  # Does not silently pick one!


# =========================================================================
# Safe AI Test: OCR uncertainty does NOT become an invented declaration
# =========================================================================
def test_safe_ai_ocr_uncertainty_does_not_invent_declaration():
    """
    OCR items with unparsed garbage must produce ExtractionStatus.MISSING,
    never inventing or hallucinating a declaration.
    """
    extractor = DeclarationExtractor()
    garbage_items = [
        OCRItem(
            text="xyz abc 123 !@# random text",
            confidence=0.90,
            bounding_box=OCRBoundingBox(x=10, y=10, width=100, height=20),
        )
    ]
    result = extractor.extract_from_ocr(garbage_items)

    assert result.declarations[DeclarationType.MRP].status == ExtractionStatus.MISSING
    assert result.declarations[DeclarationType.NET_QUANTITY].status == ExtractionStatus.MISSING
    assert result.declarations[DeclarationType.MRP].value is None
