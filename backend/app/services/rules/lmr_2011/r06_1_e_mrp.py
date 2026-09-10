"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(e)
Maximum Retail Price (MRP) Declaration rule.
"""

import re
from typing import Optional

from app.models.declaration_schemas import DeclarationType, ExtractionStatus
from app.services.rules.base import RegulatoryRule
from app.services.rules.models import (
    RuleSeverity,
    RuleFinding,
    PackageFacts,
)


class MRPDeclarationRule(RegulatoryRule):
    """
    Evaluates mandatory Maximum Retail Price (MRP) declaration under Rule 6(1)(e).
    """

    rule_id = "LMR-2011-R06-1-E"
    rule_version = "1.0.0"
    title = "Maximum Retail Price (MRP) Declaration"
    description = (
        "Every pre-packaged commodity intended for retail sale must conspicuously "
        "declare the Maximum Retail Price in Indian Rupees inclusive of all taxes."
    )
    source_reference = "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(e)"
    required_input_fields = [DeclarationType.MRP]
    severity = RuleSeverity.CRITICAL
    is_prototype = True

    def evaluate(self, facts: PackageFacts) -> RuleFinding:
        inputs_used = {"package_type": facts.package_type}

        # 1. Applicability & Statutory Exemptions (Rule 26)
        if not self.is_applicable(facts):
            return self.not_applicable_finding(
                explanation=f"Rule 6(1)(e) does not apply to package type '{facts.package_type}'.",
                input_values_used=inputs_used
            )

        # Rule 26(a) weight exemption: packages <= 10g or <= 10ml
        if facts.declared_net_weight_grams is not None and facts.declared_net_weight_grams <= 10.0:
            return self.not_applicable_finding(
                explanation="Package net weight <= 10g is exempt from retail declarations under Rule 26(a).",
                input_values_used={"declared_net_weight_grams": facts.declared_net_weight_grams}
            )
        if facts.declared_net_volume_ml is not None and facts.declared_net_volume_ml <= 10.0:
            return self.not_applicable_finding(
                explanation="Package net volume <= 10ml is exempt from retail declarations under Rule 26(a).",
                input_values_used={"declared_net_volume_ml": facts.declared_net_volume_ml}
            )

        # 2. Extract facts
        decl = facts.get_declaration(DeclarationType.MRP)
        if not decl or decl.status == ExtractionStatus.MISSING:
            return self.fail_finding(
                explanation="Mandatory Maximum Retail Price (MRP) declaration is missing on retail package under Rule 6(1)(e).",
                input_values_used={"mrp_status": "MISSING"},
                confidence=self.missing_field_confidence(facts),
            )

        evidence = self.create_evidence_references(decl, "MRP")
        inputs_used.update({
            "mrp_value": decl.value,
            "mrp_confidence": decl.confidence,
            "mrp_status": decl.status.value,
        })

        # 3. Ambiguity Resolution
        if decl.status == ExtractionStatus.AMBIGUOUS:
            return self.review_finding(
                explanation=(
                    f"Ambiguous MRP declaration: Multiple conflicting prices detected on package ({decl.notes or ''}). "
                    f"Manual review required under Rule 6(1)(e)."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        if not decl.value:
            return self.fail_finding(
                explanation="Maximum Retail Price (MRP) declaration is empty on retail package.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=1.0,
            )

        # 4. Low Confidence
        if decl.status == ExtractionStatus.LOW_CONFIDENCE or decl.confidence < 0.60:
            return self.review_finding(
                explanation=(
                    f"MRP declaration '{decl.value}' was detected with low confidence ({decl.confidence:.2f}). "
                    f"Manual inspection required to verify legibility under Rule 6(1)(e)."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        # 5. Numerical validity check
        num_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", decl.value)
        if not num_match:
            return self.fail_finding(
                explanation=f"Malformed MRP declaration '{decl.value}'. Must contain valid numerical amount.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        try:
            val = float(num_match.group(1))
            if val <= 0:
                return self.fail_finding(
                    explanation=f"Invalid MRP declaration amount ({val}). Price must be greater than zero.",
                    input_values_used=inputs_used,
                    evidence_references=evidence,
                    confidence=decl.confidence,
                )
        except ValueError:
            return self.fail_finding(
                explanation=f"Unable to parse MRP monetary amount from '{decl.value}'.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        # 6. Valid Pass
        return self.pass_finding(
            explanation=f"Compliant Maximum Retail Price declaration detected: '{decl.value}'.",
            input_values_used=inputs_used,
            evidence_references=evidence,
            confidence=decl.confidence,
        )
