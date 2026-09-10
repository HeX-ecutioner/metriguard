"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(c), Rules 11-13
Net Quantity & Metric Units Declaration rule.
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

LEGAL_METRIC_UNITS = {
    "g", "gm", "gms", "gram", "grams",
    "kg", "kgs", "kilogram", "kilograms",
    "mg", "mgs", "milligram",
    "ml", "mls", "millilitre", "millilitres", "milliliter",
    "l", "ltr", "ltrs", "litre", "litres", "liter",
    "m", "meter", "meters", "metre", "metres",
    "cm", "centimeter", "centimeters",
    "units", "unit", "nos", "pcs", "pieces", "piece", "tablets", "capsules", "n", "u",
}

ILLEGAL_NON_METRIC_PATTERNS = [
    r"\b(?:lbs?|pounds?)\b",
    r"\b(?:oz|ounces?|fl\.?\s*oz)\b",
    r"\b(?:gallons?|gal)\b",
    r"\b(?:pints?|pt)\b",
]


class NetQuantityDeclarationRule(RegulatoryRule):
    """
    Evaluates mandatory Net Quantity declaration and legal metric units under Rule 6(1)(c).
    """

    rule_id = "LMR-2011-R06-1-C"
    rule_version = "1.0.0"
    title = "Net Quantity & Metric Units Declaration"
    description = (
        "Every pre-packaged commodity must declare the net quantity in terms of standard "
        "metric units of weight, measure, or number (Rule 6(1)(c) & Rules 11-13)."
    )
    source_reference = "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(c), Rules 11-13"
    required_input_fields = [DeclarationType.NET_QUANTITY]
    severity = RuleSeverity.CRITICAL
    is_prototype = True

    def evaluate(self, facts: PackageFacts) -> RuleFinding:
        inputs_used = {"package_type": facts.package_type}

        # 1. Applicability & Exemptions (Rule 26)
        if not self.is_applicable(facts):
            return self.not_applicable_finding(
                explanation=f"Rule 6(1)(c) does not apply to package type '{facts.package_type}'.",
                input_values_used=inputs_used
            )

        # Rule 26(a): packages <= 10g or <= 10ml are exempt from net quantity declaration
        if facts.declared_net_weight_grams is not None and facts.declared_net_weight_grams <= 10.0:
            return self.not_applicable_finding(
                explanation="Package net weight <= 10g is exempt under Rule 26(a).",
                input_values_used={"declared_net_weight_grams": facts.declared_net_weight_grams}
            )
        if facts.declared_net_volume_ml is not None and facts.declared_net_volume_ml <= 10.0:
            return self.not_applicable_finding(
                explanation="Package net volume <= 10ml is exempt under Rule 26(a).",
                input_values_used={"declared_net_volume_ml": facts.declared_net_volume_ml}
            )

        # 2. Extract facts
        decl = facts.get_declaration(DeclarationType.NET_QUANTITY)
        if not decl or decl.status == ExtractionStatus.MISSING:
            return self.fail_finding(
                explanation="Mandatory Net Quantity declaration is missing under Rule 6(1)(c).",
                input_values_used={"net_quantity_status": "MISSING"},
                confidence=self.missing_field_confidence(facts),
            )

        evidence = self.create_evidence_references(decl, "NET_QUANTITY")
        inputs_used.update({
            "net_quantity_value": decl.value,
            "net_quantity_confidence": decl.confidence,
            "net_quantity_status": decl.status.value,
        })

        # 3. Ambiguity Resolution
        if decl.status == ExtractionStatus.AMBIGUOUS:
            return self.review_finding(
                explanation=(
                    f"Ambiguous Net Quantity declaration: Multiple conflicting values detected ({decl.notes or ''}). "
                    f"Manual verification required under Rule 6(1)(c)."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        if not decl.value:
            return self.fail_finding(
                explanation="Mandatory Net Quantity declaration is empty under Rule 6(1)(c).",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=1.0,
            )

        val_str = decl.value.strip()

        # 4. Low Confidence
        if decl.status == ExtractionStatus.LOW_CONFIDENCE or decl.confidence < 0.60:
            return self.review_finding(
                explanation=(
                    f"Net Quantity '{val_str}' was detected with low confidence ({decl.confidence:.2f}). "
                    f"Manual verification required."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        # 5. Check for illegal non-metric units without metric units
        val_lower = val_str.lower()
        for pattern in ILLEGAL_NON_METRIC_PATTERNS:
            if re.search(pattern, val_lower):
                has_metric = any(re.search(r"\b" + re.escape(u) + r"\b", val_lower) for u in ["g", "kg", "ml", "l"])
                if not has_metric:
                    return self.fail_finding(
                        explanation=(
                            f"Non-standard unit in Net Quantity '{val_str}'. Legal Metrology Act requires "
                            f"standard metric units (g, kg, ml, L, N). Non-metric units alone are prohibited."
                        ),
                        input_values_used=inputs_used,
                        evidence_references=evidence,
                        confidence=decl.confidence,
                    )

        # 6. Check numeric validity
        num_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", val_str)
        if not num_match:
            return self.fail_finding(
                explanation=f"Malformed Net Quantity declaration '{val_str}'. Must include numerical quantity.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        qty_num = float(num_match.group(1))
        if qty_num <= 0:
            return self.fail_finding(
                explanation=f"Invalid Net Quantity value ({qty_num}). Quantity must be greater than zero.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        # 7. Check that valid unit is present
        # Supports multipack (e.g. "300 g (4 x 75 g)") or single ("500 g")
        has_metric_unit = any(
            re.search(r"\b" + re.escape(u) + r"\b", val_lower)
            for u in ["g", "kg", "mg", "ml", "l", "units", "unit", "pcs", "pieces", "n", "u", "m", "cm"]
        )
        if not has_metric_unit:
            return self.fail_finding(
                explanation=f"Net Quantity '{val_str}' lacks recognized metric or count unit.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=decl.confidence,
            )

        # 8. Valid Pass
        return self.pass_finding(
            explanation=f"Compliant Net Quantity declaration detected: '{val_str}'.",
            input_values_used=inputs_used,
            evidence_references=evidence,
            confidence=decl.confidence,
        )
