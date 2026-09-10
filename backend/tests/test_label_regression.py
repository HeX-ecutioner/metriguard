"""
Regression tests for Legal Metrology package label compliance pipeline.
Specifically guards against false-positive non-compliance on package labels with:
- Two-column layouts (keys and values in separate horizontal bounding boxes)
- Multi-line entity declarations (Manufacturer name and address across consecutive lines)
- Statutory date variations ("Month & Year of Manufacture")
- Inline tax clauses occurring before numerical price
- Single unit count commodities (Rule 6(11) second proviso USP exemption)
- Calibrated confidence for missing declarations (never 100% without evidence)
"""

import pytest
from app.models.ocr_schemas import OCRItem, OCRBoundingBox, OCRResult
from app.models.declaration_schemas import DeclarationType, ExtractionStatus
from app.services.extraction.extractor import DeclarationExtractor
from app.services.rules.engine import RuleEngine
from app.services.rules.models import PackageFacts, RuleResult
from app.services.rules.lmr_2011 import (
    MRPDeclarationRule,
    NetQuantityDeclarationRule,
    ManufacturerPackerImporterRule,
    ManufacturePackingDateRule,
    ConsumerCareRule,
    UnitSalePriceRule,
)


@pytest.fixture
def representative_label_ocr_items():
    """
    Constructs the exact OCR items output by PaddleOCR for the representative label image:
    PRODUCT : TSHIRT XXL
    COLOUR : NAUTICAL BLUE
    NET QUANTITY : 1N
    STYLE : STY-20-21-005268
    SIZE : 58.3 cm
    M.R.P. : 999.00 (inclusive of all taxes)
    Month & Year of Manufacture : February 2022
    MANUFACTURED/ LICENSED & MARKETED BY
    BIOWORLD MERCHANDISING INDIA PVT. LTD, 307-309 PARK CENTRA, SECTOR 30
    GURGAON, HARYANA, INDIA 122001.
    FOR CUSTOMER COMPLAINTS
    Please contact our customer care cell at the address - 307-309 Park Centra, Sector 30
    Gurgaon, Haryana, INDIA 122001 or call at 0124-4362552 or e-mail at contact@bioworldind.com
    Made in India
    """
    return [
        OCRItem(text="XXL", confidence=1.0, bounding_box=OCRBoundingBox(x=622, y=67, width=108, height=62)),
        OCRItem(text="PRODUCT", confidence=1.0, bounding_box=OCRBoundingBox(x=314, y=93, width=106, height=29)),
        OCRItem(text=": TSHIRT", confidence=0.96, bounding_box=OCRBoundingBox(x=495, y=95, width=85, height=29)),
        OCRItem(text="COLOUR", confidence=1.0, bounding_box=OCRBoundingBox(x=311, y=137, width=93, height=31)),
        OCRItem(text=": NAUTICAL BLUE", confidence=0.99, bounding_box=OCRBoundingBox(x=494, y=139, width=174, height=31)),
        OCRItem(text="NET QUANTITY", confidence=0.999, bounding_box=OCRBoundingBox(x=309, y=184, width=155, height=28)),
        OCRItem(text=":1N", confidence=0.991, bounding_box=OCRBoundingBox(x=487, y=188, width=52, height=26)),
        OCRItem(text="STYLE", confidence=1.0, bounding_box=OCRBoundingBox(x=305, y=228, width=73, height=28)),
        OCRItem(text=": STY-20-21-005268", confidence=0.97, bounding_box=OCRBoundingBox(x=489, y=227, width=212, height=31)),
        OCRItem(text="SIZE", confidence=1.0, bounding_box=OCRBoundingBox(x=304, y=274, width=53, height=26)),
        OCRItem(text=": 58.3 cm", confidence=0.97, bounding_box=OCRBoundingBox(x=488, y=275, width=104, height=28)),
        OCRItem(text="M.R.P.", confidence=0.999, bounding_box=OCRBoundingBox(x=303, y=318, width=64, height=25)),
        OCRItem(text="999.00", confidence=1.0, bounding_box=OCRBoundingBox(x=482, y=317, width=207, height=49)),
        OCRItem(text="(inclusive of all taxes)", confidence=0.985, bounding_box=OCRBoundingBox(x=303, y=343, width=159, height=23)),
        OCRItem(text="Month & Year of Manufacture : February 2022", confidence=0.997, bounding_box=OCRBoundingBox(x=301, y=374, width=406, height=24)),
        OCRItem(text="MANUFACTURED/ LICENSED &", confidence=0.986, bounding_box=OCRBoundingBox(x=300, y=411, width=407, height=26)),
        OCRItem(text="MARKETED BY", confidence=0.999, bounding_box=OCRBoundingBox(x=302, y=441, width=170, height=20)),
        OCRItem(text="BIOWORLD MERCHANDISING INDIA PVT.", confidence=0.993, bounding_box=OCRBoundingBox(x=299, y=471, width=404, height=22)),
        OCRItem(text="LTD, 307-309 PARK CENTRA, SECTOR 30", confidence=0.993, bounding_box=OCRBoundingBox(x=298, y=495, width=406, height=23)),
        OCRItem(text="GURGAON, HARYANA, INDIA 122001.", confidence=0.998, bounding_box=OCRBoundingBox(x=298, y=520, width=364, height=22)),
        OCRItem(text="FOR CUSTOMER COMPLAINTS", confidence=0.999, bounding_box=OCRBoundingBox(x=295, y=566, width=368, height=28)),
        OCRItem(text="Please contact our customer care cell at the", confidence=0.998, bounding_box=OCRBoundingBox(x=295, y=600, width=407, height=25)),
        OCRItem(text="address - 307-309 Park Centra, Sector 30", confidence=0.990, bounding_box=OCRBoundingBox(x=294, y=623, width=407, height=26)),
        OCRItem(text="Gurgaon, Haryana, INDIA 122001 or call at", confidence=0.998, bounding_box=OCRBoundingBox(x=294, y=645, width=408, height=32)),
        OCRItem(text="0124-4362552", confidence=1.0, bounding_box=OCRBoundingBox(x=293, y=672, width=153, height=29)),
        OCRItem(text="or", confidence=1.0, bounding_box=OCRBoundingBox(x=492, y=675, width=27, height=22)),
        OCRItem(text="e-mail", confidence=1.0, bounding_box=OCRBoundingBox(x=567, y=672, width=62, height=23)),
        OCRItem(text="at", confidence=1.0, bounding_box=OCRBoundingBox(x=676, y=672, width=27, height=22)),
        OCRItem(text="contact@bioworldind.com", confidence=0.999, bounding_box=OCRBoundingBox(x=293, y=694, width=287, height=33)),
        OCRItem(text="Made in India", confidence=0.999, bounding_box=OCRBoundingBox(x=294, y=725, width=142, height=25)),
        OCRItem(text="FREEAUTHORITY", confidence=1.0, bounding_box=OCRBoundingBox(x=292, y=747, width=250, height=32)),
        OCRItem(text="8119050301502918", confidence=0.943, bounding_box=OCRBoundingBox(x=308, y=905, width=360, height=45)),
    ]


class TestRepresentativeLabelPipeline:
    """Tests complete extraction and rule evaluation on representative label OCR items."""

    def test_all_declarations_extracted_from_representative_label(self, representative_label_ocr_items):
        extractor = DeclarationExtractor()
        result = extractor.extract_from_ocr(representative_label_ocr_items)

        # 1. MRP
        mrp = result.declarations.get(DeclarationType.MRP)
        assert mrp is not None, "MRP declaration object must exist"
        assert mrp.status == ExtractionStatus.FOUND, f"MRP must be FOUND, got {mrp.status}"
        assert mrp.value == "Rs. 999.00", f"Expected 'Rs. 999.00', got {mrp.value}"
        assert mrp.confidence > 0.90

        # 2. Net Quantity
        net_qty = result.declarations.get(DeclarationType.NET_QUANTITY)
        assert net_qty is not None
        assert net_qty.status == ExtractionStatus.FOUND, f"Net Quantity must be FOUND, got {net_qty.status}"
        assert "1" in net_qty.value
        assert net_qty.confidence > 0.90

        # 3. Month & Year of Manufacture
        mfg_date = result.declarations.get(DeclarationType.MANUFACTURE_DATE)
        assert mfg_date is not None
        assert mfg_date.status == ExtractionStatus.FOUND, f"Mfg Date must be FOUND, got {mfg_date.status}"
        assert "Feb 2022" in mfg_date.value or "2022" in mfg_date.value
        assert mfg_date.confidence > 0.90

        # 4. Manufacturer Name & Address
        mfr = result.declarations.get(DeclarationType.MANUFACTURER)
        assert mfr is not None
        assert mfr.status == ExtractionStatus.FOUND, f"Manufacturer must be FOUND, got {mfr.status}"
        assert "BIOWORLD MERCHANDISING" in mfr.value
        assert "PARK CENTRA" in mfr.value
        assert "122001" in mfr.value
        assert mfr.confidence > 0.90

        # 5. Country of Origin
        coo = result.declarations.get(DeclarationType.COUNTRY_OF_ORIGIN)
        assert coo is not None
        assert coo.status == ExtractionStatus.FOUND
        assert coo.value == "India"

    def test_representative_label_passes_rule_engine(self, representative_label_ocr_items):
        extractor = DeclarationExtractor()
        extraction_result = extractor.extract_from_ocr(representative_label_ocr_items)
        engine = RuleEngine()
        compliance_result = engine.evaluate_extraction(
            extraction_result=extraction_result,
            package_type="retail",
            is_imported=False,
        )

        assert compliance_result.overall_status == "COMPLIANT", (
            f"Representative label must be COMPLIANT, got {compliance_result.overall_status}. "
            f"Failures: {[f.rule_id + ': ' + f.explanation for f in compliance_result.findings if f.result == RuleResult.FAIL]}"
        )

        # Confirm all 4 previously failing rules now pass
        findings_by_rule = {f.rule_id: f for f in compliance_result.findings}
        assert findings_by_rule["LMR-2011-R06-1-E"].result == RuleResult.PASS
        assert findings_by_rule["LMR-2011-R06-1-C"].result == RuleResult.PASS
        assert findings_by_rule["LMR-2011-R06-1-A"].result == RuleResult.PASS
        assert findings_by_rule["LMR-2011-R06-1-D"].result == RuleResult.PASS

        # Confirm Rule 6(11) USP is NOT_APPLICABLE for single unit count commodity (1N)
        assert findings_by_rule["LMR-2011-R06-11-USP"].result == RuleResult.NOT_APPLICABLE
        assert "second proviso" in findings_by_rule["LMR-2011-R06-11-USP"].explanation.lower()


class TestMissingDeclarationConfidenceCalibration:
    """
    Tests that missing declaration rules never assign or display 100% confidence
    when negative findings lack affirmative visual evidence.
    """

    def test_missing_mrp_confidence_calibrated(self):
        rule = MRPDeclarationRule()
        facts = PackageFacts(declarations={}, package_type="retail", overall_confidence=0.95)
        finding = rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "missing" in finding.explanation.lower()
        assert finding.confidence < 1.0, "Missing MRP must NOT have 100% confidence"
        assert finding.confidence <= 0.70

    def test_missing_net_quantity_confidence_calibrated(self):
        rule = NetQuantityDeclarationRule()
        facts = PackageFacts(declarations={}, package_type="retail", overall_confidence=0.90)
        finding = rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert finding.confidence < 1.0, "Missing Net Quantity must NOT have 100% confidence"
        assert finding.confidence <= 0.70

    def test_missing_entity_confidence_calibrated(self):
        rule = ManufacturerPackerImporterRule()
        facts = PackageFacts(declarations={}, package_type="retail", overall_confidence=0.88)
        finding = rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert finding.confidence < 1.0, "Missing Entity must NOT have 100% confidence"
        assert finding.confidence <= 0.70

    def test_missing_date_confidence_calibrated(self):
        rule = ManufacturePackingDateRule()
        facts = PackageFacts(declarations={}, package_type="retail", overall_confidence=0.92)
        finding = rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert finding.confidence < 1.0, "Missing Date must NOT have 100% confidence"
        assert finding.confidence <= 0.70

    def test_missing_consumer_care_confidence_calibrated(self):
        rule = ConsumerCareRule()
        facts = PackageFacts(declarations={}, package_type="retail", overall_confidence=0.85)
        finding = rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert finding.confidence < 1.0, "Missing Consumer Care must NOT have 100% confidence"
        assert finding.confidence <= 0.70


class TestRule611USPSecondProviso:
    """Tests the statutory second proviso of Rule 6(11) for single unit packages."""

    def test_single_unit_number_exempt(self):
        from app.models.declaration_schemas import ExtractedDeclaration, ExtractionStatus
        rule = UnitSalePriceRule()
        decl = ExtractedDeclaration(
            declaration_type=DeclarationType.NET_QUANTITY,
            status=ExtractionStatus.FOUND,
            value="1 units",
            confidence=0.95,
        )
        facts = PackageFacts(
            declarations={DeclarationType.NET_QUANTITY: decl},
            package_type="retail"
        )
        finding = rule.evaluate(facts)
        assert finding.result == RuleResult.NOT_APPLICABLE
        assert "second proviso" in finding.explanation.lower()

    def test_single_n_notation_exempt(self):
        from app.models.declaration_schemas import ExtractedDeclaration, ExtractionStatus
        rule = UnitSalePriceRule()
        decl = ExtractedDeclaration(
            declaration_type=DeclarationType.NET_QUANTITY,
            status=ExtractionStatus.FOUND,
            value="1 N",
            confidence=0.95,
        )
        facts = PackageFacts(
            declarations={DeclarationType.NET_QUANTITY: decl},
            package_type="retail"
        )
        finding = rule.evaluate(facts)
        assert finding.result == RuleResult.NOT_APPLICABLE
        assert "second proviso" in finding.explanation.lower()
