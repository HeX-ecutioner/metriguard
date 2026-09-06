"""
Abstract base class for versioned regulatory compliance rules.
Enforces typed metadata, applicability gating, and deterministic evaluation contracts.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.models.declaration_schemas import DeclarationType, ExtractedDeclaration
from app.services.rules.models import (
    RuleResult,
    RuleSeverity,
    RuleFinding,
    RuleApplicability,
    PackageFacts,
    EvidenceReference,
)


class RegulatoryRule(ABC):
    """
    Abstract base class for all versioned Legal Metrology compliance rules.
    Every rule must be deterministic, reproducible, and backed by statutory authority.
    """

    rule_id: str
    rule_version: str = "1.0.0"
    title: str
    description: str
    applicability: RuleApplicability = RuleApplicability()
    required_input_fields: List[DeclarationType] = []
    severity: RuleSeverity = RuleSeverity.ERROR
    evidence_requirements: List[str] = ["bounding_box", "original_text", "confidence"]
    enabled: bool = True
    is_prototype: bool = True
    source_reference: str

    def is_applicable(self, facts: PackageFacts) -> bool:
        """
        Determines whether this rule applies to the package under evaluation.
        Evaluates package type, category, weight/volume limits, and import status.
        """
        # 1. Package Type exclusion (e.g. wholesale, industrial, institutional)
        pkg_type = (facts.package_type or "retail").lower()
        if self.applicability.excluded_package_types:
            for excl in self.applicability.excluded_package_types:
                if excl.lower() == pkg_type:
                    return False

        # 2. Package Type inclusion
        if self.applicability.package_types:
            matching_type = any(
                req.lower() == pkg_type
                for req in self.applicability.package_types
            )
            if not matching_type:
                return False

        # 3. Commodity Category filter if specified
        if self.applicability.commodity_categories:
            if not facts.commodity_category or facts.commodity_category.lower() not in [
                c.lower() for c in self.applicability.commodity_categories
            ]:
                return False

        # 4. Import status requirement if specified
        if self.applicability.requires_imported is not None:
            if facts.is_imported != self.applicability.requires_imported:
                return False

        # 5. Net weight thresholds
        if self.applicability.min_net_weight_grams is not None:
            if (
                facts.declared_net_weight_grams is not None
                and facts.declared_net_weight_grams < self.applicability.min_net_weight_grams
            ):
                return False

        if self.applicability.max_net_weight_grams is not None:
            if (
                facts.declared_net_weight_grams is not None
                and facts.declared_net_weight_grams > self.applicability.max_net_weight_grams
            ):
                return False

        # 6. Net volume thresholds
        if self.applicability.min_net_volume_ml is not None:
            if (
                facts.declared_net_volume_ml is not None
                and facts.declared_net_volume_ml < self.applicability.min_net_volume_ml
            ):
                return False

        if self.applicability.max_net_volume_ml is not None:
            if (
                facts.declared_net_volume_ml is not None
                and facts.declared_net_volume_ml > self.applicability.max_net_volume_ml
            ):
                return False

        return True

    @abstractmethod
    def evaluate(self, facts: PackageFacts) -> RuleFinding:
        """
        Executes the deterministic evaluation of this rule against package facts.
        Must return a RuleFinding with PASS, FAIL, REVIEW, or NOT_APPLICABLE.
        """
        pass

    # --- Helper Factories for Findings ---

    def create_evidence_references(
        self,
        declaration: Optional[ExtractedDeclaration],
        field_name: str
    ) -> List[EvidenceReference]:
        """Builds an audit evidence reference from an extracted declaration."""
        if not declaration:
            return []
        bbox_dict = declaration.bounding_box.model_dump() if declaration.bounding_box else None
        return [
            EvidenceReference(
                source_image_id=declaration.source_image_id,
                bounding_box=bbox_dict,
                original_text=declaration.original_ocr_text,
                confidence=declaration.confidence,
                field_name=field_name,
            )
        ]

    def pass_finding(
        self,
        explanation: str,
        input_values_used: Dict[str, Any],
        evidence_references: Optional[List[EvidenceReference]] = None,
        confidence: float = 1.0,
    ) -> RuleFinding:
        return RuleFinding(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            result=RuleResult.PASS,
            explanation=explanation,
            severity=self.severity,
            confidence=confidence,
            input_values_used=input_values_used,
            evidence_references=evidence_references or [],
            requires_manual_review=False,
        )

    def fail_finding(
        self,
        explanation: str,
        input_values_used: Dict[str, Any],
        evidence_references: Optional[List[EvidenceReference]] = None,
        confidence: float = 1.0,
    ) -> RuleFinding:
        return RuleFinding(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            result=RuleResult.FAIL,
            explanation=explanation,
            severity=self.severity,
            confidence=confidence,
            input_values_used=input_values_used,
            evidence_references=evidence_references or [],
            requires_manual_review=False,
        )

    def review_finding(
        self,
        explanation: str,
        input_values_used: Dict[str, Any],
        evidence_references: Optional[List[EvidenceReference]] = None,
        confidence: float = 0.5,
    ) -> RuleFinding:
        return RuleFinding(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            result=RuleResult.REVIEW,
            explanation=explanation,
            severity=self.severity,
            confidence=confidence,
            input_values_used=input_values_used,
            evidence_references=evidence_references or [],
            requires_manual_review=True,
        )

    def not_applicable_finding(
        self,
        explanation: str,
        input_values_used: Dict[str, Any],
    ) -> RuleFinding:
        return RuleFinding(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            result=RuleResult.NOT_APPLICABLE,
            explanation=explanation,
            severity=RuleSeverity.INFO,
            confidence=1.0,
            input_values_used=input_values_used,
            evidence_references=[],
            requires_manual_review=False,
        )
