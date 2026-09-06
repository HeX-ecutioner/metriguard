"""
Core domain models for MetriGuard's deterministic regulatory rule engine.
Independent from FastAPI, React, SQLite, and external frameworks.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
import re
from pydantic import BaseModel, Field, ConfigDict

from app.models.declaration_schemas import (
    DeclarationType,
    ExtractionStatus,
    ExtractedDeclaration,
    DeclarationExtractionResult,
)


class RuleResult(str, Enum):
    """Evaluation outcome for a regulatory rule."""
    PASS = "PASS"                      # Compliant with statutory requirements
    FAIL = "FAIL"                      # Statutory non-compliance / violation detected
    REVIEW = "REVIEW"                  # Ambiguous, low-confidence, or requires human inspection
    NOT_APPLICABLE = "NOT_APPLICABLE"  # Legally exempt or condition not triggered


class RuleSeverity(str, Enum):
    """Regulatory violation severity."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EvidenceReference(BaseModel):
    """Traceable OCR/fact evidence linking a rule finding back to source pixels/text."""
    model_config = ConfigDict(from_attributes=True)

    source_image_id: Optional[Union[int, str]] = None
    bounding_box: Optional[Dict[str, int]] = None
    original_text: Optional[str] = None
    confidence: float = 1.0
    field_name: str = ""


class RuleFinding(BaseModel):
    """
    Standardized, reproducible result of evaluating one rule against package facts.
    """
    model_config = ConfigDict(from_attributes=True)

    rule_id: str = Field(..., description="Unique rule identifier (e.g. LMR-2011-R06-1-E)")
    rule_version: str = Field(..., description="Semantic version of the rule (e.g. 1.0.0)")
    result: RuleResult = Field(..., description="PASS, FAIL, REVIEW, or NOT_APPLICABLE")
    explanation: str = Field(..., description="Human-readable legal and technical justification")
    severity: RuleSeverity = Field(..., description="Violation severity classification")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score in the finding")
    input_values_used: Dict[str, Any] = Field(default_factory=dict, description="Facts evaluated by the rule")
    evidence_references: List[EvidenceReference] = Field(default_factory=list, description="Audit evidence references")
    requires_manual_review: bool = Field(default=False, description="Flag indicating human verification required")


class RuleApplicability(BaseModel):
    """Criteria specifying when a rule applies to a commodity package."""
    package_types: List[str] = Field(default_factory=lambda: ["retail"])
    excluded_package_types: List[str] = Field(default_factory=lambda: ["wholesale", "industrial", "institutional"])
    commodity_categories: Optional[List[str]] = None
    min_net_weight_grams: Optional[float] = None
    max_net_weight_grams: Optional[float] = None
    min_net_volume_ml: Optional[float] = None
    max_net_volume_ml: Optional[float] = None
    requires_imported: Optional[bool] = None


class PackageFacts(BaseModel):
    """
    Structured factual representations of a package to be evaluated by the rule engine.
    Completely decoupled from rule execution logic.
    """
    model_config = ConfigDict(from_attributes=True)

    declarations: Dict[DeclarationType, ExtractedDeclaration] = Field(default_factory=dict)
    package_type: str = Field(default="retail", description="retail, wholesale, industrial, institutional")
    commodity_category: Optional[str] = Field(None, description="Commodity classification if known")
    declared_net_weight_grams: Optional[float] = None
    declared_net_volume_ml: Optional[float] = None
    is_imported: bool = Field(default=False, description="True if commodity is imported")
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    image_id: Optional[Union[int, str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_declaration(self, decl_type: DeclarationType) -> Optional[ExtractedDeclaration]:
        """Convenience accessor for extracted declaration by type."""
        return self.declarations.get(decl_type)

    @classmethod
    def from_extraction_result(
        cls,
        extraction_result: DeclarationExtractionResult,
        package_type: str = "retail",
        commodity_category: Optional[str] = None,
        is_imported: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PackageFacts":
        """
        Factory method to convert a DeclarationExtractionResult from the OCR extraction
        layer into PackageFacts for rule evaluation.
        """
        facts = cls(
            declarations=extraction_result.declarations,
            package_type=package_type,
            commodity_category=commodity_category,
            is_imported=is_imported,
            image_id=extraction_result.image_id,
            metadata=metadata or {},
        )

        # Parse numeric net weight/volume if net quantity declaration is available
        net_qty_decl = facts.get_declaration(DeclarationType.NET_QUANTITY)
        if net_qty_decl and net_qty_decl.value:
            val_str = net_qty_decl.value.lower()
            # Check mass
            mass_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(kg|kgs|kilogram|g|gm|gms|gram|mg)", val_str)
            if mass_match:
                num = float(mass_match.group(1))
                unit = mass_match.group(2)
                if unit in ("kg", "kgs", "kilogram"):
                    facts.declared_net_weight_grams = num * 1000.0
                elif unit in ("g", "gm", "gms", "gram"):
                    facts.declared_net_weight_grams = num
                elif unit == "mg":
                    facts.declared_net_weight_grams = num / 1000.0

            # Check volume
            vol_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(l|ltr|ltrs|litre|litres|liter|ml|mls|millilitre)", val_str)
            if vol_match:
                num = float(vol_match.group(1))
                unit = vol_match.group(2)
                if unit in ("l", "ltr", "ltrs", "litre", "litres", "liter"):
                    facts.declared_net_volume_ml = num * 1000.0
                elif unit in ("ml", "mls", "millilitre"):
                    facts.declared_net_volume_ml = num

        return facts


class ComplianceEvaluationResult(BaseModel):
    """
    Synthesized outcome of running the deterministic rule engine over package facts.
    """
    model_config = ConfigDict(from_attributes=True)

    overall_status: str = Field(..., description="COMPLIANT, NON_COMPLIANT, MANUAL_REVIEW, NOT_APPLICABLE")
    findings: List[RuleFinding] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict, description="Counts by RuleResult")
    requires_manual_review: bool = Field(default=False)
    evaluation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = Field(default="1.0.0")
