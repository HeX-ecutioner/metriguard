"""
Deterministic regulatory rule engine for MetriGuard.
Evaluates structured package facts against versioned rules without LLM intervention.
Synthesizes reproducible compliance determinations.
"""

from collections import defaultdict
from typing import Optional, List
from datetime import datetime, timezone

from app.models.declaration_schemas import DeclarationExtractionResult
from app.services.rules.models import (
    RuleResult,
    RuleFinding,
    PackageFacts,
    ComplianceEvaluationResult,
)
from app.services.rules.registry import RuleRegistry, get_rule_registry


class RuleEngine:
    """
    Deterministic rule evaluation engine.
    Applies registered Legal Metrology rules to package facts.
    """

    def __init__(self, registry: Optional[RuleRegistry] = None, engine_version: str = "1.0.0"):
        self.registry = registry or get_rule_registry()
        self.engine_version = engine_version

    def evaluate(self, facts: PackageFacts) -> ComplianceEvaluationResult:
        """
        Executes all active rules in the registry against package facts.
        Synthesizes an overall compliance result based on individual findings.
        """
        rules = self.registry.get_all_rules(only_enabled=True)
        findings: List[RuleFinding] = []
        summary: Dict[str, int] = defaultdict(int)
        requires_manual_review = False

        for rule in rules:
            finding = rule.evaluate(facts)
            findings.append(finding)
            summary[finding.result.value] += 1
            if finding.result == RuleResult.REVIEW or finding.requires_manual_review:
                requires_manual_review = True

        # Synthesize overall status:
        # 1. Any FAIL -> NON_COMPLIANT
        # 2. Any REVIEW -> MANUAL_REVIEW
        # 3. All NOT_APPLICABLE -> NOT_APPLICABLE
        # 4. At least one PASS and zero FAIL/REVIEW -> COMPLIANT
        fail_count = summary[RuleResult.FAIL.value]
        review_count = summary[RuleResult.REVIEW.value]
        pass_count = summary[RuleResult.PASS.value]
        na_count = summary[RuleResult.NOT_APPLICABLE.value]

        if fail_count > 0:
            overall_status = "NON_COMPLIANT"
        elif review_count > 0:
            overall_status = "MANUAL_REVIEW"
        elif pass_count > 0:
            overall_status = "COMPLIANT"
        elif na_count > 0 and (pass_count == 0 and fail_count == 0 and review_count == 0):
            overall_status = "NOT_APPLICABLE"
        else:
            # Fallback if no rules were evaluated
            overall_status = "MANUAL_REVIEW"
            requires_manual_review = True

        return ComplianceEvaluationResult(
            overall_status=overall_status,
            findings=findings,
            summary=dict(summary),
            requires_manual_review=requires_manual_review,
            evaluation_timestamp=datetime.now(timezone.utc),
            engine_version=self.engine_version,
        )

    def evaluate_extraction(
        self,
        extraction_result: DeclarationExtractionResult,
        package_type: str = "retail",
        commodity_category: Optional[str] = None,
        is_imported: bool = False,
    ) -> ComplianceEvaluationResult:
        """
        Convenience adapter to evaluate declarations directly from the extraction layer.
        """
        facts = PackageFacts.from_extraction_result(
            extraction_result=extraction_result,
            package_type=package_type,
            commodity_category=commodity_category,
            is_imported=is_imported,
        )
        return self.evaluate(facts)


def evaluate_package_compliance(
    facts: PackageFacts,
    registry: Optional[RuleRegistry] = None
) -> ComplianceEvaluationResult:
    """Convenience helper for compliance evaluation."""
    engine = RuleEngine(registry=registry)
    return engine.evaluate(facts)
