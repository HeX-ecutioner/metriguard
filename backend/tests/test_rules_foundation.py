"""
Unit tests for MetriGuard's deterministic regulatory rule-engine foundation.
Tests every rule against all 7 mandatory scenarios:
1. Valid case
2. Invalid case
3. Missing field
4. Malformed field
5. Ambiguous field
6. Not-applicable case
7. Low-confidence case

Also tests engine orchestrator synthesis and extraction result adapter.
Keeps rule engine independent from FastAPI, React, SQLite, and OCR.
"""

import pytest
from app.models.declaration_schemas import (
    DeclarationType,
    ExtractionStatus,
    ExtractedDeclaration,
    ExtractionCandidate,
    DeclarationExtractionResult,
)
from app.models.ocr_schemas import OCRBoundingBox
from app.services.rules import (
    RuleResult,
    RuleSeverity,
    PackageFacts,
    RuleEngine,
    get_rule_registry,
    MRPDeclarationRule,
    NetQuantityDeclarationRule,
    ManufacturerPackerImporterRule,
    ManufacturePackingDateRule,
    ConsumerCareRule,
    UnitSalePriceRule,
)


def make_declaration(
    decl_type: DeclarationType,
    value: str,
    confidence: float = 0.95,
    status: ExtractionStatus = ExtractionStatus.FOUND,
    notes: str = ""
) -> ExtractedDeclaration:
    """Helper to construct an ExtractedDeclaration for testing."""
    bbox = OCRBoundingBox(x=10, y=10, width=100, height=20)
    candidate = ExtractionCandidate(
        declaration_type=decl_type,
        raw_value=value,
        normalized_value=value,
        confidence=confidence,
        original_ocr_text=f"{decl_type.value}: {value}",
        bounding_box=bbox,
        pattern_name="test_pattern",
        is_ambiguous=(status == ExtractionStatus.AMBIGUOUS),
    )
    return ExtractedDeclaration(
        declaration_type=decl_type,
        status=status,
        value=value if status != ExtractionStatus.AMBIGUOUS else None,
        confidence=confidence,
        candidates=[candidate],
        bounding_box=bbox,
        original_ocr_text=f"{decl_type.value}: {value}",
        notes=notes,
    )


# ============================================================================
# 1. MRPDeclarationRule (Rule 6(1)(e)) Tests - All 7 Scenarios
# ============================================================================

class TestMRPDeclarationRule:
    rule = MRPDeclarationRule()

    def test_valid(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MRP: make_declaration(DeclarationType.MRP, "Rs. 150.00")
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.PASS
        assert "Compliant Maximum Retail Price" in finding.explanation
        assert finding.requires_manual_review is False

    def test_invalid_zero_or_negative_price(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MRP: make_declaration(DeclarationType.MRP, "Rs. 0.00")
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "greater than zero" in finding.explanation

    def test_missing_field(self):
        facts = PackageFacts(declarations={}, package_type="retail")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "missing" in finding.explanation.lower()

    def test_malformed_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MRP: make_declaration(DeclarationType.MRP, "Rs. INVALID_TEXT")
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Malformed" in finding.explanation

    def test_ambiguous_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MRP: make_declaration(
                    DeclarationType.MRP, "Rs. 150.00",
                    status=ExtractionStatus.AMBIGUOUS,
                    notes="Conflicting values detected: Rs. 150 vs Rs. 180"
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True
        assert "Ambiguous MRP declaration" in finding.explanation

    def test_not_applicable_wholesale_or_weight_exempt(self):
        # Wholesale package
        wholesale_facts = PackageFacts(declarations={}, package_type="wholesale")
        finding_wholesale = self.rule.evaluate(wholesale_facts)
        assert finding_wholesale.result == RuleResult.NOT_APPLICABLE

        # Rule 26 weight exempt (<= 10g)
        exempt_facts = PackageFacts(
            declarations={},
            package_type="retail",
            declared_net_weight_grams=5.0
        )
        finding_exempt = self.rule.evaluate(exempt_facts)
        assert finding_exempt.result == RuleResult.NOT_APPLICABLE
        assert "Rule 26" in finding_exempt.explanation

    def test_low_confidence(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MRP: make_declaration(
                    DeclarationType.MRP, "Rs. 150.00",
                    confidence=0.45,
                    status=ExtractionStatus.LOW_CONFIDENCE
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True
        assert "low confidence" in finding.explanation.lower()


# ============================================================================
# 2. NetQuantityDeclarationRule (Rule 6(1)(c)) Tests - All 7 Scenarios
# ============================================================================

class TestNetQuantityDeclarationRule:
    rule = NetQuantityDeclarationRule()

    def test_valid(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g")
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.PASS
        assert "Compliant Net Quantity" in finding.explanation

    def test_invalid_illegal_non_metric_units(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "2 lbs")
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Non-standard unit" in finding.explanation

    def test_missing_field(self):
        facts = PackageFacts(declarations={}, package_type="retail")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "missing" in finding.explanation.lower()

    def test_malformed_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "NOT_A_QUANTITY")
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Malformed" in finding.explanation

    def test_ambiguous_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(
                    DeclarationType.NET_QUANTITY, "500 g",
                    status=ExtractionStatus.AMBIGUOUS,
                    notes="Conflicting: 500g vs 250g"
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True
        assert "Ambiguous Net Quantity" in finding.explanation

    def test_not_applicable_rule_26_exempt(self):
        facts = PackageFacts(
            declarations={},
            package_type="retail",
            declared_net_weight_grams=8.0  # <= 10g exempt
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.NOT_APPLICABLE
        assert "Rule 26" in finding.explanation

    def test_low_confidence(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(
                    DeclarationType.NET_QUANTITY, "500 g",
                    confidence=0.40,
                    status=ExtractionStatus.LOW_CONFIDENCE
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True
        assert "low confidence" in finding.explanation.lower()


# ============================================================================
# 3. ManufacturerPackerImporterRule (Rule 6(1)(a)) Tests - All 7 Scenarios
# ============================================================================

class TestManufacturerPackerImporterRule:
    rule = ManufacturerPackerImporterRule()

    def test_valid(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURER: make_declaration(
                    DeclarationType.MANUFACTURER,
                    "Parle Products Pvt Ltd, Vile Parle, Mumbai - 400057"
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.PASS
        assert "Compliant MANUFACTURER declaration" in finding.explanation

    def test_invalid_imported_without_importer(self):
        # When imported is True, missing importer is a violation even if manufacturer is present
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURER: make_declaration(
                    DeclarationType.MANUFACTURER, "Foreign Goods LLC, Tokyo"
                )
            },
            package_type="retail",
            is_imported=True
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Importer" in finding.explanation

    def test_missing_field(self):
        facts = PackageFacts(declarations={}, package_type="retail")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "missing" in finding.explanation.lower()

    def test_malformed_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURER: make_declaration(DeclarationType.MANUFACTURER, "N/A")
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Malformed" in finding.explanation

    def test_ambiguous_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURER: make_declaration(
                    DeclarationType.MANUFACTURER, "ABC Ltd",
                    status=ExtractionStatus.AMBIGUOUS
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True

    def test_not_applicable_wholesale(self):
        facts = PackageFacts(declarations={}, package_type="wholesale")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.NOT_APPLICABLE

    def test_low_confidence(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURER: make_declaration(
                    DeclarationType.MANUFACTURER, "ABC Foods Pvt Ltd, Mumbai",
                    confidence=0.48,
                    status=ExtractionStatus.LOW_CONFIDENCE
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True


# ============================================================================
# 4. ManufacturePackingDateRule (Rule 6(1)(d)) Tests - All 7 Scenarios
# ============================================================================

class TestManufacturePackingDateRule:
    rule = ManufacturePackingDateRule()

    def test_valid(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURE_DATE: make_declaration(
                    DeclarationType.MANUFACTURE_DATE, "10/2025"
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.PASS

    def test_invalid_post_dated_future(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURE_DATE: make_declaration(
                    DeclarationType.MANUFACTURE_DATE, "01/2099"
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "future" in finding.explanation.lower()

    def test_missing_field(self):
        facts = PackageFacts(declarations={}, package_type="retail")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "missing" in finding.explanation.lower()

    def test_malformed_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURE_DATE: make_declaration(
                    DeclarationType.MANUFACTURE_DATE, "10/1850"  # Absurd historical date
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Invalid" in finding.explanation

    def test_ambiguous_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURE_DATE: make_declaration(
                    DeclarationType.MANUFACTURE_DATE, "10/2025",
                    status=ExtractionStatus.AMBIGUOUS
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True

    def test_not_applicable_wholesale(self):
        facts = PackageFacts(declarations={}, package_type="wholesale")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.NOT_APPLICABLE

    def test_low_confidence(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.MANUFACTURE_DATE: make_declaration(
                    DeclarationType.MANUFACTURE_DATE, "10/2025",
                    confidence=0.45,
                    status=ExtractionStatus.LOW_CONFIDENCE
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True


# ============================================================================
# 5. ConsumerCareRule (Rule 6(1)(g)) Tests - All 7 Scenarios
# ============================================================================

class TestConsumerCareRule:
    rule = ConsumerCareRule()

    def test_valid(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.CONSUMER_CARE: make_declaration(
                    DeclarationType.CONSUMER_CARE, "1800-222-3333, care@brand.com"
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.PASS

    def test_invalid_malformed(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.CONSUMER_CARE: make_declaration(
                    DeclarationType.CONSUMER_CARE, "N/A"
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Malformed" in finding.explanation

    def test_missing_field(self):
        facts = PackageFacts(declarations={}, package_type="retail")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "missing" in finding.explanation.lower()

    def test_ambiguous_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.CONSUMER_CARE: make_declaration(
                    DeclarationType.CONSUMER_CARE, "1800-111-2222",
                    status=ExtractionStatus.AMBIGUOUS
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True

    def test_not_applicable_wholesale(self):
        facts = PackageFacts(declarations={}, package_type="wholesale")
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.NOT_APPLICABLE

    def test_low_confidence(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.CONSUMER_CARE: make_declaration(
                    DeclarationType.CONSUMER_CARE, "1800-111-2222",
                    confidence=0.40,
                    status=ExtractionStatus.LOW_CONFIDENCE
                )
            },
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True


# ============================================================================
# 6. UnitSalePriceRule (Rule 6(11)) Tests - All 7 Scenarios
# ============================================================================

class TestUnitSalePriceRule:
    rule = UnitSalePriceRule()

    def test_valid(self):
        # Package > 100g with valid USP
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(DeclarationType.UNIT_SALE_PRICE, "Rs. 0.30 / g"),
            },
            package_type="retail",
            declared_net_weight_grams=500.0
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.PASS
        assert "Compliant Unit Sale Price" in finding.explanation

    def test_invalid_exceeds_threshold_but_missing_usp(self):
        # Package > 100g but USP missing -> FAIL
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g"),
            },
            package_type="retail",
            declared_net_weight_grams=500.0
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "exceeds 100g/100ml" in finding.explanation

    def test_missing_net_quantity_uncertain_applicability(self):
        # When net quantity is completely missing/unknown -> cannot determine applicability -> REVIEW
        facts = PackageFacts(
            declarations={},
            package_type="retail"
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True
        assert "Net quantity is unknown" in finding.explanation

    def test_malformed_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "250 g"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(DeclarationType.UNIT_SALE_PRICE, "USP: INVALID"),
            },
            package_type="retail",
            declared_net_weight_grams=250.0
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.FAIL
        assert "Malformed" in finding.explanation

    def test_ambiguous_field(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(
                    DeclarationType.UNIT_SALE_PRICE, "Rs. 0.30 / g",
                    status=ExtractionStatus.AMBIGUOUS
                ),
            },
            package_type="retail",
            declared_net_weight_grams=500.0
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True

    def test_not_applicable_under_100g(self):
        # Package <= 100g is NOT APPLICABLE under Rule 6(11)
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "50 g")
            },
            package_type="retail",
            declared_net_weight_grams=50.0
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.NOT_APPLICABLE
        assert "<= 100g" in finding.explanation

    def test_low_confidence(self):
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(
                    DeclarationType.UNIT_SALE_PRICE, "Rs. 0.30 / g",
                    confidence=0.45,
                    status=ExtractionStatus.LOW_CONFIDENCE
                ),
            },
            package_type="retail",
            declared_net_weight_grams=500.0
        )
        finding = self.rule.evaluate(facts)
        assert finding.result == RuleResult.REVIEW
        assert finding.requires_manual_review is True


# ============================================================================
# 7. RuleEngine Orchestrator & Synthesis Tests
# ============================================================================

class TestRuleEngineOrchestrator:

    def test_full_compliant_package(self):
        engine = RuleEngine()
        facts = PackageFacts(
            declarations={
                DeclarationType.MRP: make_declaration(DeclarationType.MRP, "Rs. 150.00"),
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g"),
                DeclarationType.MANUFACTURER: make_declaration(DeclarationType.MANUFACTURER, "ABC Foods Pvt Ltd, Mumbai"),
                DeclarationType.MANUFACTURE_DATE: make_declaration(DeclarationType.MANUFACTURE_DATE, "10/2025"),
                DeclarationType.CONSUMER_CARE: make_declaration(DeclarationType.CONSUMER_CARE, "1800-111-2222"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(DeclarationType.UNIT_SALE_PRICE, "Rs. 0.30 / g"),
            },
            package_type="retail",
            declared_net_weight_grams=500.0
        )
        result = engine.evaluate(facts)
        assert result.overall_status == "COMPLIANT"
        assert result.requires_manual_review is False
        assert result.summary["PASS"] == 6
        assert result.summary["FAIL"] == 0

    def test_failing_package_becomes_non_compliant(self):
        engine = RuleEngine()
        # Missing MRP should fail
        facts = PackageFacts(
            declarations={
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g"),
                DeclarationType.MANUFACTURER: make_declaration(DeclarationType.MANUFACTURER, "ABC Foods Pvt Ltd, Mumbai"),
                DeclarationType.MANUFACTURE_DATE: make_declaration(DeclarationType.MANUFACTURE_DATE, "10/2025"),
                DeclarationType.CONSUMER_CARE: make_declaration(DeclarationType.CONSUMER_CARE, "1800-111-2222"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(DeclarationType.UNIT_SALE_PRICE, "Rs. 0.30 / g"),
            },
            package_type="retail",
            declared_net_weight_grams=500.0
        )
        result = engine.evaluate(facts)
        assert result.overall_status == "NON_COMPLIANT"
        assert result.summary["FAIL"] >= 1

    def test_ambiguous_package_becomes_manual_review(self):
        engine = RuleEngine()
        facts = PackageFacts(
            declarations={
                DeclarationType.MRP: make_declaration(
                    DeclarationType.MRP, "Rs. 150.00",
                    status=ExtractionStatus.AMBIGUOUS
                ),
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "500 g"),
                DeclarationType.MANUFACTURER: make_declaration(DeclarationType.MANUFACTURER, "ABC Foods Ltd"),
                DeclarationType.MANUFACTURE_DATE: make_declaration(DeclarationType.MANUFACTURE_DATE, "10/2025"),
                DeclarationType.CONSUMER_CARE: make_declaration(DeclarationType.CONSUMER_CARE, "1800-111-2222"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(DeclarationType.UNIT_SALE_PRICE, "Rs. 0.30 / g"),
            },
            package_type="retail",
            declared_net_weight_grams=500.0
        )
        result = engine.evaluate(facts)
        # Any review without failure results in MANUAL_REVIEW
        assert result.overall_status == "MANUAL_REVIEW"
        assert result.requires_manual_review is True

    def test_wholesale_package_not_applicable(self):
        engine = RuleEngine()
        facts = PackageFacts(declarations={}, package_type="wholesale")
        result = engine.evaluate(facts)
        assert result.overall_status == "NOT_APPLICABLE"
        assert result.summary["NOT_APPLICABLE"] == 6

    def test_evaluate_from_extraction_result_adapter(self):
        engine = RuleEngine()
        extraction_res = DeclarationExtractionResult(
            image_id="img_999",
            declarations={
                DeclarationType.MRP: make_declaration(DeclarationType.MRP, "Rs. 99.00"),
                DeclarationType.NET_QUANTITY: make_declaration(DeclarationType.NET_QUANTITY, "200 g"),
                DeclarationType.MANUFACTURER: make_declaration(DeclarationType.MANUFACTURER, "Pure Ltd, Delhi"),
                DeclarationType.MANUFACTURE_DATE: make_declaration(DeclarationType.MANUFACTURE_DATE, "09/2025"),
                DeclarationType.CONSUMER_CARE: make_declaration(DeclarationType.CONSUMER_CARE, "care@pure.in"),
                DeclarationType.UNIT_SALE_PRICE: make_declaration(DeclarationType.UNIT_SALE_PRICE, "Rs. 0.50 / g"),
            },
        )
        result = engine.evaluate_extraction(extraction_res, package_type="retail")
        assert result.overall_status == "COMPLIANT"
        assert len(result.findings) == 6
