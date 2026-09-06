"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(11) (2021/2022 Amendment)
Unit Sale Price (USP) declaration rule.
"""

import re

from app.models.declaration_schemas import DeclarationType, ExtractionStatus
from app.services.rules.base import RegulatoryRule
from app.services.rules.models import (
    RuleSeverity,
    RuleFinding,
    PackageFacts,
)


class UnitSalePriceRule(RegulatoryRule):
    """
    Evaluates mandatory Unit Sale Price declaration for packages > 100g/ml under Rule 6(11).
    """

    rule_id = "LMR-2011-R06-11-USP"
    rule_version = "1.0.0"
    title = "Unit Sale Price (USP)"
    description = (
        "Pre-packaged commodities where net quantity exceeds 100g or 100ml must declare "
        "the Unit Sale Price in terms of per gram, per kilogram, per ml, per litre, or per number (Rule 6(11))."
    )
    source_reference = "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(11) [GSR 779(E)]"
    required_input_fields = [
        DeclarationType.UNIT_SALE_PRICE,
        DeclarationType.NET_QUANTITY,
    ]
    severity = RuleSeverity.WARNING
    is_prototype = True

    def evaluate(self, facts: PackageFacts) -> RuleFinding:
        inputs_used = {"package_type": facts.package_type}

        # 1. Base applicability & Exemptions
        if not self.is_applicable(facts):
            return self.not_applicable_finding(
                explanation=f"Rule 6(11) does not apply to package type '{facts.package_type}'.",
                input_values_used=inputs_used
            )

        # 2. Check Net Quantity to determine whether Rule 6(11) triggers
        net_qty_decl = facts.get_declaration(DeclarationType.NET_QUANTITY)
        net_weight = facts.declared_net_weight_grams
        net_volume = facts.declared_net_volume_ml

        # If net quantity is completely missing or unknown, applicability is uncertain
        if (
            (not net_qty_decl or net_qty_decl.status == ExtractionStatus.MISSING or not net_qty_decl.value)
            and net_weight is None
            and net_volume is None
        ):
            return self.review_finding(
                explanation=(
                    "Net quantity is unknown; cannot verify whether package exceeds 100g/100ml "
                    "to determine Unit Sale Price applicability under Rule 6(11). Manual inspection required."
                ),
                input_values_used={"net_quantity": "UNKNOWN"},
                confidence=0.5,
            )

        # Determine if threshold (> 100g or > 100ml) is exceeded
        exceeds_threshold = False
        if net_weight is not None and net_weight > 100.0:
            exceeds_threshold = True
            inputs_used["declared_net_weight_grams"] = net_weight
        elif net_volume is not None and net_volume > 100.0:
            exceeds_threshold = True
            inputs_used["declared_net_volume_ml"] = net_volume
        elif net_qty_decl and net_qty_decl.value:
            # Fallback parse from string (e.g. "500 g", "1 kg", "250 ml")
            val_lower = net_qty_decl.value.lower()
            num_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", val_lower)
            if num_match:
                num = float(num_match.group(1))
                if any(u in val_lower for u in ["kg", "l", "ltr"]):
                    exceeds_threshold = True
                elif any(u in val_lower for u in ["g", "gm", "ml"]) and num > 100.0:
                    exceeds_threshold = True

        # If package is <= 100g/100ml, Rule 6(11) is NOT APPLICABLE
        if not exceeds_threshold and (net_weight is not None or net_volume is not None):
            return self.not_applicable_finding(
                explanation=(
                    "Unit Sale Price declaration is not applicable for package net quantity <= 100g / 100ml "
                    "under Rule 6(11)."
                ),
                input_values_used={
                    "declared_net_weight_grams": net_weight,
                    "declared_net_volume_ml": net_volume,
                }
            )

        # 3. Applicable package (> 100g/ml): Check Unit Sale Price declaration
        usp_decl = facts.get_declaration(DeclarationType.UNIT_SALE_PRICE)
        if not usp_decl or usp_decl.status == ExtractionStatus.MISSING:
            return self.fail_finding(
                explanation=(
                    "Package net quantity exceeds 100g/100ml, but mandatory Unit Sale Price (USP) "
                    "declaration is missing under Rule 6(11)."
                ),
                input_values_used={"usp_status": "MISSING", "threshold_exceeded": True},
                confidence=1.0,
            )

        evidence = self.create_evidence_references(usp_decl, "UNIT_SALE_PRICE")
        inputs_used.update({
            "usp_value": usp_decl.value,
            "confidence": usp_decl.confidence,
            "status": usp_decl.status.value,
        })

        # 4. Ambiguity Resolution
        if usp_decl.status == ExtractionStatus.AMBIGUOUS:
            return self.review_finding(
                explanation=(
                    f"Ambiguous Unit Sale Price declaration: Multiple conflicting values detected ({usp_decl.notes or ''}). "
                    f"Manual review required under Rule 6(11)."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=usp_decl.confidence,
            )

        if not usp_decl.value:
            return self.fail_finding(
                explanation="Mandatory Unit Sale Price (USP) declaration is empty under Rule 6(11).",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=1.0,
            )

        val_str = usp_decl.value.strip()

        # 5. Low Confidence
        if usp_decl.status == ExtractionStatus.LOW_CONFIDENCE or usp_decl.confidence < 0.60:
            return self.review_finding(
                explanation=(
                    f"Unit Sale Price '{val_str}' was detected with low confidence ({usp_decl.confidence:.2f}). "
                    f"Manual verification required."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=usp_decl.confidence,
            )

        # 6. Format check: must contain rate and per unit
        if not re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:\/|per)\s*([a-zA-Z]+)", val_str, re.IGNORECASE):
            return self.fail_finding(
                explanation=f"Malformed Unit Sale Price declaration '{val_str}'. Expected format like 'Rs. 0.30 / g'.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=usp_decl.confidence,
            )

        # 7. Valid Pass
        return self.pass_finding(
            explanation=f"Compliant Unit Sale Price declaration detected: '{val_str}'.",
            input_values_used=inputs_used,
            evidence_references=evidence,
            confidence=usp_decl.confidence,
        )
