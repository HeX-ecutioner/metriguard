"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(g) & Rule 6(2)
Consumer Care Grievance Redressal rule.
"""

from app.models.declaration_schemas import DeclarationType, ExtractionStatus
from app.services.rules.base import RegulatoryRule
from app.services.rules.models import (
    RuleSeverity,
    RuleFinding,
    PackageFacts,
)


class ConsumerCareRule(RegulatoryRule):
    """
    Evaluates mandatory Consumer Care grievance redressal declaration under Rule 6(1)(g).
    """

    rule_id = "LMR-2011-R06-1-G"
    rule_version = "1.0.0"
    title = "Consumer Care Grievance Channel"
    description = (
        "Every pre-packaged commodity must declare consumer care contact details "
        "(telephone number, email address, or grievance address) under Rule 6(1)(g)."
    )
    source_reference = "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(g), Rule 6(2)"
    required_input_fields = [DeclarationType.CONSUMER_CARE]
    severity = RuleSeverity.WARNING
    is_prototype = True

    def evaluate(self, facts: PackageFacts) -> RuleFinding:
        inputs_used = {"package_type": facts.package_type}

        # 1. Applicability & Exemptions
        if not self.is_applicable(facts):
            return self.not_applicable_finding(
                explanation=f"Rule 6(1)(g) does not apply to package type '{facts.package_type}'.",
                input_values_used=inputs_used
            )

        # 2. Extract facts
        decl = facts.get_declaration(DeclarationType.CONSUMER_CARE)
        if not decl or decl.status == ExtractionStatus.MISSING:
            return self.fail_finding(
                explanation="Mandatory Consumer Care contact details are missing under Rule 6(1)(g).",
                input_values_used={"consumer_care_status": "MISSING"},
                confidence=1.0,
            )

        evidence = self.create_evidence_references(decl, "CONSUMER_CARE")
        inputs_used.update({
            "consumer_care_value": decl.value,
            "confidence": decl.confidence,
            "status": decl.status.value,
        })

        # 3. Ambiguity Resolution
        if decl.status == ExtractionStatus.AMBIGUOUS:
            return self.review_finding(
                explanation=(
                    f"Ambiguous Consumer Care declaration: Multiple conflicting contact details detected ({decl.notes or ''}). "
                    f"Manual review required under Rule 6(1)(g)."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        if not decl.value:
            return self.fail_finding(
                explanation="Mandatory Consumer Care contact details are empty under Rule 6(1)(g).",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=1.0,
            )

        val_str = decl.value.strip()

        # 4. Low Confidence
        if decl.status == ExtractionStatus.LOW_CONFIDENCE or decl.confidence < 0.60:
            return self.review_finding(
                explanation=(
                    f"Consumer Care contact details '{val_str}' were detected with low confidence ({decl.confidence:.2f}). "
                    f"Manual verification required."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        # 5. Completeness / Malformed check
        if len(val_str) < 4 or val_str.lower() in ("n/a", "none", "null", "care"):
            return self.fail_finding(
                explanation=f"Malformed or incomplete Consumer Care declaration: '{val_str}'.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        # 6. Valid Pass
        return self.pass_finding(
            explanation=f"Compliant Consumer Care contact channel detected: '{val_str}'.",
            input_values_used=inputs_used,
            evidence_references=evidence,
            confidence=decl.confidence,
        )
