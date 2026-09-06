"""
Comprehensive unit and integration test suite for MetriGuard declaration extraction.
Tests deterministic parsing, Indian packaging formats, OCR error handling,
multi-candidate resolution, ambiguity detection, traceability, and compliance decoupling.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.ocr_schemas import OCRItem, OCRBoundingBox, OCRResult, PreprocessingMetadata
from app.models.declaration_schemas import (
    DeclarationType,
    ExtractionStatus,
    DeclarationExtractionResult,
)
from app.services.extraction import (
    DeclarationExtractor,
    extract_declarations,
)
from app.services.extraction.patterns import (
    normalize_mrp,
    normalize_net_quantity,
    normalize_unit_sale_price,
    normalize_date,
    normalize_country,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def extractor():
    return DeclarationExtractor()


# 1. Clean Text Scenario
def test_clean_text_extraction(extractor):
    sample_text = """
    Commodity: Refined Sunflower Oil
    Manufactured by: ABC Foods Private Limited, Mumbai
    Packed by: XYZ Packaging Hub, Gujarat
    Country of Origin: India
    Net Quantity: 500 g
    MRP: Rs. 150.00 (inclusive of all taxes)
    Unit Sale Price: Rs. 0.30 / g
    Mfg Date: 15/10/2025
    Date of Packing: 20/10/2025
    Best Before: 12 months from mfg
    Use By: 15/10/2026
    Consumer Care: 1800-123-4567, care@abcfoods.com
    """
    result = extractor.extract_from_ocr(sample_text, image_id=101)

    assert isinstance(result, DeclarationExtractionResult)
    assert result.has_ambiguities is False

    # Check MRP
    mrp = result.declarations[DeclarationType.MRP]
    assert mrp.status == ExtractionStatus.FOUND
    assert mrp.value == "Rs. 150.00"

    # Check Net Quantity
    net_qty = result.declarations[DeclarationType.NET_QUANTITY]
    assert net_qty.status == ExtractionStatus.FOUND
    assert "500" in net_qty.value and "g" in net_qty.value

    # Check Unit Sale Price
    usp = result.declarations[DeclarationType.UNIT_SALE_PRICE]
    assert usp.status == ExtractionStatus.FOUND
    assert "0.30" in usp.value and "/ g" in usp.value

    # Check Dates
    mfg = result.declarations[DeclarationType.MANUFACTURE_DATE]
    assert mfg.status == ExtractionStatus.FOUND
    assert "15/10/2025" in mfg.value

    pkd = result.declarations[DeclarationType.PACKING_DATE]
    assert pkd.status == ExtractionStatus.FOUND
    assert "20/10/2025" in pkd.value

    bb = result.declarations[DeclarationType.BEST_BEFORE]
    assert bb.status == ExtractionStatus.FOUND
    assert "12 months from mfg" in bb.value

    use_by = result.declarations[DeclarationType.USE_BY]
    assert use_by.status == ExtractionStatus.FOUND
    assert "15/10/2026" in use_by.value

    # Check Country & Entity
    origin = result.declarations[DeclarationType.COUNTRY_OF_ORIGIN]
    assert origin.status == ExtractionStatus.FOUND
    assert origin.value == "India"

    mfr = result.declarations[DeclarationType.MANUFACTURER]
    assert mfr.status == ExtractionStatus.FOUND
    assert "ABC Foods" in mfr.value

    pkr = result.declarations[DeclarationType.PACKER]
    assert pkr.status == ExtractionStatus.FOUND
    assert "XYZ Packaging" in pkr.value

    care = result.declarations[DeclarationType.CONSUMER_CARE]
    assert care.status == ExtractionStatus.FOUND
    assert "1800-123-4567" in care.value


# 2. Mixed Uppercase and Lowercase Scenario
def test_mixed_case_handling(extractor):
    lines = [
        "mrp: rs. 175.50",
        "net quantity: 1 ltr",
        "mfg date: 05/2025",
        "country of origin: INDIA",
        "unit sale price: rs. 175.50 / L",
    ]
    result = extractor.extract_from_ocr(lines, image_id="img_mixed_case")

    assert result.declarations[DeclarationType.MRP].value == "Rs. 175.50"
    assert "1 L" in result.declarations[DeclarationType.NET_QUANTITY].value
    assert result.declarations[DeclarationType.MANUFACTURE_DATE].value == "05/2025"
    assert result.declarations[DeclarationType.COUNTRY_OF_ORIGIN].value == "India"
    assert "175.50" in result.declarations[DeclarationType.UNIT_SALE_PRICE].value


# 3. Punctuation Variations Scenario
@pytest.mark.parametrize("mrp_raw, expected_norm", [
    ("MRP: Rs. 150/-", "Rs. 150.00"),
    ("M.R.P. 150", "Rs. 150.00"),
    ("MRP = 150", "Rs. 150.00"),
    ("MRP - 150.50/-", "Rs. 150.50"),
    ("MRP: ₹ 249.00", "Rs. 249.00"),
    ("M.R.P.: Rs 99/- (INCL. OF ALL TAXES)", "Rs. 99.00"),
])
def test_mrp_punctuation_variations(extractor, mrp_raw, expected_norm):
    result = extractor.extract_from_ocr([mrp_raw])
    mrp_decl = result.declarations[DeclarationType.MRP]
    assert mrp_decl.status == ExtractionStatus.FOUND
    assert mrp_decl.value == expected_norm


@pytest.mark.parametrize("qty_raw, expected_norm", [
    ("NET WT: 500 G.", "500 g"),
    ("NET WT - 500g", "500 g"),
    ("Net Quantity = 1 kg", "1 kg"),
    ("Net Qty: 750 ml.", "750 ml"),
    ("Net Content: 10 N", "10 units"),
])
def test_net_quantity_punctuation_variations(extractor, qty_raw, expected_norm):
    result = extractor.extract_from_ocr([qty_raw])
    qty_decl = result.declarations[DeclarationType.NET_QUANTITY]
    assert qty_decl.status == ExtractionStatus.FOUND
    assert qty_decl.value == expected_norm


# 4. OCR Spelling Errors Scenario
def test_ocr_spelling_errors(extractor):
    typo_lines = [
        "M.B.P. Rs 250/-",         # MBP instead of MRP
        "Nel Wt 400g",             # Nel Wt instead of Net Wt
        "Mfq Date 11/2025",        # Mfq instead of Mfg
        "Mfq by Pure Foods Ltd",   # Mfq by instead of Mfd by
    ]
    result = extractor.extract_from_ocr(typo_lines)

    # MBP typo -> MRP extracted
    mrp = result.declarations[DeclarationType.MRP]
    assert mrp.status == ExtractionStatus.FOUND
    assert mrp.value == "Rs. 250.00"

    # Nel Wt -> NET_QUANTITY extracted
    net_qty = result.declarations[DeclarationType.NET_QUANTITY]
    assert net_qty.status == ExtractionStatus.FOUND
    assert net_qty.value == "400 g"

    # Mfq Date -> MANUFACTURE_DATE extracted
    mfg = result.declarations[DeclarationType.MANUFACTURE_DATE]
    assert mfg.status == ExtractionStatus.FOUND
    assert mfg.value == "11/2025"

    # Mfq by -> MANUFACTURER extracted
    mfr = result.declarations[DeclarationType.MANUFACTURER]
    assert mfr.status == ExtractionStatus.FOUND
    assert "Pure Foods" in mfr.value


# 5. Multiple Quantities (Multipack) Scenario
def test_multipack_net_quantity(extractor):
    text = "Net Quantity: 4 x 75g = 300g"
    result = extractor.extract_from_ocr([text])
    net_qty = result.declarations[DeclarationType.NET_QUANTITY]

    assert net_qty.status == ExtractionStatus.FOUND
    assert "300 g" in net_qty.value
    assert "4 x 75 g" in net_qty.value
    assert len(net_qty.candidates) >= 1
    assert net_qty.candidates[0].original_ocr_text == text


# 6. Multiple Dates on Same Label Scenario
def test_multiple_distinct_dates_separation(extractor):
    items = [
        OCRItem(
            text="MFG DATE: 01/01/2025",
            confidence=0.98,
            bounding_box=OCRBoundingBox(x=10, y=10, width=150, height=20)
        ),
        OCRItem(
            text="PKD DATE: 05/01/2025",
            confidence=0.97,
            bounding_box=OCRBoundingBox(x=10, y=40, width=150, height=20)
        ),
        OCRItem(
            text="BEST BEFORE 12 MONTHS FROM PACKING",
            confidence=0.96,
            bounding_box=OCRBoundingBox(x=10, y=70, width=250, height=20)
        ),
        OCRItem(
            text="EXPIRY DATE: 05/01/2026",
            confidence=0.99,
            bounding_box=OCRBoundingBox(x=10, y=100, width=180, height=20)
        ),
    ]
    result = extractor.extract_from_ocr(items)

    # Ensure all 4 dates are accurately categorized without cross-contamination
    assert result.declarations[DeclarationType.MANUFACTURE_DATE].value == "01/01/2025"
    assert result.declarations[DeclarationType.PACKING_DATE].value == "05/01/2025"
    assert "12 months from packing" in result.declarations[DeclarationType.BEST_BEFORE].value
    assert result.declarations[DeclarationType.USE_BY].value == "05/01/2026"


# 7. Missing Declarations Scenario
def test_missing_declarations(extractor):
    minimal_text = "MRP Rs. 50\nNet Wt: 100g"
    result = extractor.extract_from_ocr(minimal_text)

    # FOUND
    assert result.declarations[DeclarationType.MRP].status == ExtractionStatus.FOUND
    assert result.declarations[DeclarationType.NET_QUANTITY].status == ExtractionStatus.FOUND

    # MISSING declarations
    assert result.declarations[DeclarationType.IMPORTER].status == ExtractionStatus.MISSING
    assert result.declarations[DeclarationType.IMPORTER].value is None
    assert result.declarations[DeclarationType.COUNTRY_OF_ORIGIN].status == ExtractionStatus.MISSING
    assert result.declarations[DeclarationType.CONSUMER_CARE].status == ExtractionStatus.MISSING

    # Summary verification
    assert result.summary[ExtractionStatus.FOUND.value] == 2
    assert result.summary[ExtractionStatus.MISSING.value] == 11


# 8. Ambiguous MRP Conflict Scenario
def test_ambiguous_mrp_detection(extractor):
    conflicting_items = [
        OCRItem(
            text="Front Panel: MRP Rs. 150/-",
            confidence=0.95,
            bounding_box=OCRBoundingBox(x=50, y=50, width=120, height=30)
        ),
        OCRItem(
            text="Back Panel: MRP Rs. 180/-",
            confidence=0.92,
            bounding_box=OCRBoundingBox(x=50, y=200, width=120, height=30)
        )
    ]
    result = extractor.extract_from_ocr(conflicting_items)

    mrp_decl = result.declarations[DeclarationType.MRP]
    assert mrp_decl.status == ExtractionStatus.AMBIGUOUS
    assert mrp_decl.value is None  # Never silently pick one
    assert result.has_ambiguities is True
    assert len(mrp_decl.candidates) == 2
    assert all(c.is_ambiguous for c in mrp_decl.candidates)
    assert "conflicting values detected" in mrp_decl.notes.lower()


# 9. Multilingual & Noisy Text Scenario
def test_multilingual_noisy_text(extractor):
    multilingual_text = [
        "अधिकतम खुदरा मूल्य MRP Rs. 199.00 (सभी कर सहित)",
        "शुद्ध वजन Net Wt: 250 g",
        "उत्पादन तिथि Mfg Date: 08/2025",
        "भारत में निर्मित Country of Origin: India",
    ]
    result = extractor.extract_from_ocr(multilingual_text)

    assert result.declarations[DeclarationType.MRP].value == "Rs. 199.00"
    assert result.declarations[DeclarationType.NET_QUANTITY].value == "250 g"
    assert result.declarations[DeclarationType.MANUFACTURE_DATE].value == "08/2025"
    assert result.declarations[DeclarationType.COUNTRY_OF_ORIGIN].value == "India"


# 10. Evidence Traceability
def test_evidence_traceability(extractor):
    box = OCRBoundingBox(x=120, y=340, width=200, height=45)
    item = OCRItem(
        text="MRP: Rs. 350/-",
        confidence=0.94,
        bounding_box=box,
        page_or_region_id="back_label"
    )
    result = extractor.extract_from_ocr([item], image_id=42)

    mrp = result.declarations[DeclarationType.MRP]
    assert mrp.source_image_id == 42
    assert mrp.bounding_box == box
    assert mrp.original_ocr_text == "MRP: Rs. 350/-"
    assert mrp.confidence == 0.94

    assert len(mrp.candidates) == 1
    candidate = mrp.candidates[0]
    assert candidate.raw_value == "350/-"
    assert candidate.normalized_value == "Rs. 350.00"
    assert candidate.page_or_region_id == "back_label"
    assert candidate.pattern_name == "mrp_standard"


# 11. Decoupling from Legal Compliance
def test_compliance_decoupling(extractor):
    """Verifies that extraction does not evaluate compliance or produce violations."""
    result = extractor.extract_from_ocr("MRP Rs. 100\nNet Wt 50g")
    result_dict = result.model_dump()

    assert "violations" not in result_dict
    assert "compliance_status" not in result_dict
    assert "is_compliant" not in result_dict
    assert "penalty" not in result_dict


# 12. Direct API Endpoint Tests
def test_direct_extraction_api_with_text(client):
    payload = {
        "text": "MRP Rs. 299/-\nNet Wt: 1 kg\nCountry of Origin: India",
        "image_id": "test_img_01"
    }
    response = client.post("/api/v1/extract/declarations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["image_id"] == "test_img_01"
    assert data["declarations"]["MRP"]["value"] == "Rs. 299.00"
    assert data["declarations"]["NET_QUANTITY"]["value"] == "1 kg"
    assert data["declarations"]["COUNTRY_OF_ORIGIN"]["value"] == "India"
    assert data["summary"]["FOUND"] == 3


def test_direct_extraction_api_with_items(client):
    payload = {
        "items": [
            {
                "text": "MRP: Rs. 450/-",
                "confidence": 0.95,
                "bounding_box": {"x": 10, "y": 10, "width": 100, "height": 20},
                "page_or_region_id": "p1"
            }
        ],
        "image_id": 99
    }
    response = client.post("/api/v1/extract/declarations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["declarations"]["MRP"]["value"] == "Rs. 450.00"
    assert data["declarations"]["MRP"]["bounding_box"]["x"] == 10


def test_extraction_from_ocr_result_api(client):
    ocr_result_payload = {
        "image_id": "pkg_ocr_55",
        "recognized_text": "MRP Rs. 500\nNet Wt: 2 kg",
        "confidence": 0.96,
        "items": [
            {
                "text": "MRP Rs. 500",
                "confidence": 0.98,
                "bounding_box": {"x": 5, "y": 5, "width": 80, "height": 20}
            },
            {
                "text": "Net Wt: 2 kg",
                "confidence": 0.95,
                "bounding_box": {"x": 5, "y": 30, "width": 80, "height": 20}
            }
        ],
        "preprocessing_metadata": {
            "original_width": 800,
            "original_height": 600
        },
        "provider_name": "mock_ocr",
        "processing_duration_ms": 12.5
    }
    response = client.post("/api/v1/extract/ocr-result", json=ocr_result_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["declarations"]["MRP"]["value"] == "Rs. 500.00"
    assert data["declarations"]["NET_QUANTITY"]["value"] == "2 kg"


def test_low_confidence_declaration(extractor):
    """Verifies that items with low confidence are marked as LOW_CONFIDENCE rather than FOUND."""
    low_conf_item = OCRItem(
        text="MRP Rs. 99",
        confidence=0.40,  # Below default 0.60 threshold
        bounding_box=OCRBoundingBox(x=10, y=10, width=50, height=20)
    )
    result = extractor.extract_from_ocr([low_conf_item])
    mrp = result.declarations[DeclarationType.MRP]

    assert mrp.status == ExtractionStatus.LOW_CONFIDENCE
    assert mrp.value == "Rs. 99.00"
    assert mrp.confidence == 0.40
    assert "low confidence" in mrp.notes.lower()


def test_importer_and_usp_patterns(extractor):
    lines = [
        "Imported by: Global Importers India Pvt Ltd, Nariman Point, Mumbai - 400021",
        "USP: Rs. 2.50 / unit",
        "Consumer Care: Call 1800-200-3000 or Email support@brand.in",
    ]
    result = extractor.extract_from_ocr(lines)

    imp = result.declarations[DeclarationType.IMPORTER]
    assert imp.status == ExtractionStatus.FOUND
    assert "Global Importers" in imp.value

    usp = result.declarations[DeclarationType.UNIT_SALE_PRICE]
    assert usp.status == ExtractionStatus.FOUND
    assert "Rs. 2.50 / units" in usp.value or "Rs. 2.50 / unit" in usp.value

    care = result.declarations[DeclarationType.CONSUMER_CARE]
    assert care.status == ExtractionStatus.FOUND
    assert "1800-200-3000" in care.value


def test_inspection_session_extraction_and_persistence(client):
    """
    Integration test:
    - Creates an inspection
    - Uploads a test image
    - Triggers declaration extraction
    - Verifies declarations are saved to DB
    - Verifies NO compliance violations or pass/fail decisions are generated
    """
    from app.services.inspection_orchestrator import get_inspection_orchestrator, InspectionOrchestrator
    from app.services.ocr.mock_provider import MockOCRProvider
    from app.services.ocr.service import OCRService, get_ocr_service

    mock_svc = OCRService(provider=MockOCRProvider())
    mock_orch = InspectionOrchestrator(ocr_service=mock_svc)
    app.dependency_overrides[get_inspection_orchestrator] = lambda: mock_orch
    app.dependency_overrides[get_ocr_service] = lambda: mock_svc

    try:

        # 1. Create inspection
        create_resp = client.post("/api/v1/inspections", json={"product_name": "Test Cookies"})
        assert create_resp.status_code == 201
        insp_id = create_resp.json()["id"]

        # 2. Upload image (100x100 white PNG)
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        upload_resp = client.post(
            f"/api/v1/inspections/{insp_id}/images",
            files={"file": ("cookie_label.png", buf.getvalue(), "image/png")}
        )
        assert upload_resp.status_code == 201
        img_id = upload_resp.json()["id"]

        # 3. Check prior counts before running extraction
        pre_insp = client.get(f"/api/v1/inspections/{insp_id}").json()
        pre_violations_count = len(pre_insp.get("violations", []))
        pre_declarations_count = len(pre_insp.get("declarations", []))

        # 4. Trigger extraction endpoint
        extract_resp = client.post(f"/api/v1/extract/inspections/{insp_id}")
        assert extract_resp.status_code == 200
        extraction_data = extract_resp.json()
        assert "declarations" in extraction_data
        assert "violations" not in extraction_data

        # 5. Fetch inspection via GET and verify declarations persisted
        get_insp = client.get(f"/api/v1/inspections/{insp_id}")
        assert get_insp.status_code == 200
        insp_data = get_insp.json()

        # Verify declarations were added to DB
        assert len(insp_data["declarations"]) > pre_declarations_count
        saved_decl = [d for d in insp_data["declarations"] if d["source_image_id"] == img_id]
        assert len(saved_decl) > 0
        assert "declaration_type" in saved_decl[0]
        assert "extracted_value" in saved_decl[0]

        # Strictly verify compliance decoupling:
        # No new violations were created by the extraction endpoint
        assert len(insp_data["violations"]) == pre_violations_count
    finally:
        app.dependency_overrides.pop(get_inspection_orchestrator, None)
        app.dependency_overrides.pop(get_ocr_service, None)


