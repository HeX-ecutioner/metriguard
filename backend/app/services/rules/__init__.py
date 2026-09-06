"""
MetriGuard Deterministic Regulatory Rule Engine Subsystem.
Enforces compliance rules based strictly on the Legal Metrology (Packaged Commodities) Rules, 2011.
Decoupled from OCR, FastAPI, React, and database layers.
"""

from app.services.rules.models import (
    RuleResult,
    RuleSeverity,
    EvidenceReference,
    RuleFinding,
    RuleApplicability,
    PackageFacts,
    ComplianceEvaluationResult,
)
from app.services.rules.base import RegulatoryRule
from app.services.rules.registry import RuleRegistry, get_rule_registry
from app.services.rules.engine import RuleEngine, evaluate_package_compliance
from app.services.rules.lmr_2011 import (
    MRPDeclarationRule,
    NetQuantityDeclarationRule,
    ManufacturerPackerImporterRule,
    ManufacturePackingDateRule,
    ConsumerCareRule,
    UnitSalePriceRule,
    get_lmr_2011_prototype_rules,
)

__all__ = [
    "RuleResult",
    "RuleSeverity",
    "EvidenceReference",
    "RuleFinding",
    "RuleApplicability",
    "PackageFacts",
    "ComplianceEvaluationResult",
    "RegulatoryRule",
    "RuleRegistry",
    "get_rule_registry",
    "RuleEngine",
    "evaluate_package_compliance",
    "MRPDeclarationRule",
    "NetQuantityDeclarationRule",
    "ManufacturerPackerImporterRule",
    "ManufacturePackingDateRule",
    "ConsumerCareRule",
    "UnitSalePriceRule",
    "get_lmr_2011_prototype_rules",
]
