"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(d)
Month and Year of Manufacture / Pre-packing rule.
"""

import re
from datetime import datetime, timezone

from app.models.declaration_schemas import DeclarationType, ExtractionStatus
from app.services.rules.base import RegulatoryRule
from app.services.rules.models import (
    RuleSeverity,
    RuleFinding,
    PackageFacts,
)


class ManufacturePackingDateRule(RegulatoryRule):
    """
    Evaluates mandatory Month and Year of Manufacture or Pre-packing under Rule 6(1)(d).
    """

    rule_id = "LMR-2011-R06-1-D"
    rule_version = "1.0.0"
    title = "Date of Manufacture or Pre-packing"
    description = (
        "Every pre-packaged commodity must declare the month and year of manufacture "
        "or pre-packing or import (Rule 6(1)(d))."
    )
    source_reference = "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(d)"
    required_input_fields = [
        DeclarationType.MANUFACTURE_DATE,
        DeclarationType.PACKING_DATE,
    ]
    severity = RuleSeverity.ERROR
    is_prototype = True

    def evaluate(self, facts: PackageFacts) -> RuleFinding:
        inputs_used = {"package_type": facts.package_type}

        # 1. Applicability & Exemptions
        if not self.is_applicable(facts):
            return self.not_applicable_finding(
                explanation=f"Rule 6(1)(d) does not apply to package type '{facts.package_type}'.",
                input_values_used=inputs_used
            )

        # 2. Extract facts
        mfg_decl = facts.get_declaration(DeclarationType.MANUFACTURE_DATE)
        pkd_decl = facts.get_declaration(DeclarationType.PACKING_DATE)

        # Select available date declaration
        candidates = [d for d in [mfg_decl, pkd_decl] if d and d.status != ExtractionStatus.MISSING]
        if not candidates:
            return self.fail_finding(
                explanation="Mandatory month and year of manufacture or pre-packing is missing under Rule 6(1)(d).",
                input_values_used={"date_status": "MISSING"},
                confidence=1.0,
            )

        ambiguous_candidates = [d for d in candidates if d.status == ExtractionStatus.AMBIGUOUS]
        if ambiguous_candidates:
            target_decl = ambiguous_candidates[0]
        else:
            target_decl = max(candidates, key=lambda d: d.confidence)

        field_name = target_decl.declaration_type.value
        evidence = self.create_evidence_references(target_decl, field_name)

        inputs_used.update({
            "selected_date_type": field_name,
            "date_value": target_decl.value,
            "confidence": target_decl.confidence,
            "status": target_decl.status.value,
        })

        # 3. Ambiguity Resolution
        if target_decl.status == ExtractionStatus.AMBIGUOUS:
            return self.review_finding(
                explanation=(
                    f"Ambiguous {field_name} declaration: Multiple conflicting dates detected ({target_decl.notes or ''}). "
                    f"Manual review required under Rule 6(1)(d)."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=target_decl.confidence,
            )

        if not target_decl.value:
            return self.fail_finding(
                explanation=f"Empty {field_name} declaration detected on package.",
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=1.0,
            )

        val_str = target_decl.value.strip()

        # 4. Low Confidence
        if target_decl.status == ExtractionStatus.LOW_CONFIDENCE or target_decl.confidence < 0.60:
            return self.review_finding(
                explanation=(
                    f"{field_name} '{val_str}' was detected with low confidence ({target_decl.confidence:.2f}). "
                    f"Manual verification required."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=target_decl.confidence,
            )

        # 5. Format & Plausibility check (year cannot be wildly in the future or absurd past)
        year_match = re.search(r"\b([0-9]{4})\b", val_str)
        if year_match:
            year_val = int(year_match.group(1))
            current_year = datetime.now(timezone.utc).year
            # In India, post-dating a package beyond current year + 1 is illegal/malformed
            if year_val > current_year + 1:
                return self.fail_finding(
                    explanation=(
                        f"Post-dated {field_name} '{val_str}' detected. Declared year {year_val} "
                        f"is in the future."
                    ),
                    input_values_used=inputs_used,
                    evidence_references=evidence,
                    confidence=target_decl.confidence,
                )
            if year_val < 2000:
                return self.fail_finding(
                    explanation=f"Invalid {field_name} '{val_str}'. Historical year {year_val} is invalid.",
                    input_values_used=inputs_used,
                    evidence_references=evidence,
                    confidence=target_decl.confidence,
                )

        # 6. Valid Pass
        return self.pass_finding(
            explanation=f"Compliant {field_name} declaration detected: '{val_str}'.",
            input_values_used=inputs_used,
            evidence_references=evidence,
            confidence=target_decl.confidence,
        )
