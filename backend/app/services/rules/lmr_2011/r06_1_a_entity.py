"""
Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(a)
Name and Address of Manufacturer / Packer / Importer rule.
"""

from app.models.declaration_schemas import DeclarationType, ExtractionStatus
from app.services.rules.base import RegulatoryRule
from app.services.rules.models import (
    RuleSeverity,
    RuleFinding,
    PackageFacts,
)


class ManufacturerPackerImporterRule(RegulatoryRule):
    """
    Evaluates mandatory Manufacturer, Packer, or Importer declaration under Rule 6(1)(a).
    """

    rule_id = "LMR-2011-R06-1-A"
    rule_version = "1.0.0"
    title = "Manufacturer / Packer / Importer Identity"
    description = (
        "Every pre-packaged commodity must declare the name and complete address of the "
        "manufacturer, packer, or importer (Rule 6(1)(a))."
    )
    source_reference = "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(a)"
    required_input_fields = [
        DeclarationType.MANUFACTURER,
        DeclarationType.PACKER,
        DeclarationType.IMPORTER,
    ]
    severity = RuleSeverity.ERROR
    is_prototype = True

    def evaluate(self, facts: PackageFacts) -> RuleFinding:
        inputs_used = {
            "package_type": facts.package_type,
            "is_imported": facts.is_imported,
        }

        # 1. Applicability & Exemptions
        if not self.is_applicable(facts):
            return self.not_applicable_finding(
                explanation=f"Rule 6(1)(a) does not apply to package type '{facts.package_type}'.",
                input_values_used=inputs_used
            )

        # 2. Extract declarations
        mfr_decl = facts.get_declaration(DeclarationType.MANUFACTURER)
        pkr_decl = facts.get_declaration(DeclarationType.PACKER)
        imp_decl = facts.get_declaration(DeclarationType.IMPORTER)

        # Imported commodity check
        if facts.is_imported:
            if not imp_decl or imp_decl.status == ExtractionStatus.MISSING:
                return self.fail_finding(
                    explanation="Imported commodity must declare the name and address of the Importer under Rule 6(1)(a).",
                    input_values_used={"is_imported": True, "importer_status": "MISSING"},
                    confidence=1.0,
                )
            target_decl = imp_decl
            field_name = "IMPORTER"
        else:
            # For domestic package, any of MFR, PACKER, or IMPORTER satisfies base obligation
            candidates = [d for d in [mfr_decl, pkr_decl, imp_decl] if d and d.status != ExtractionStatus.MISSING]
            if not candidates:
                return self.fail_finding(
                    explanation="Name and complete address of Manufacturer, Packer, or Importer is missing under Rule 6(1)(a).",
                    input_values_used={"entity_status": "MISSING"},
                    confidence=1.0,
                )
            # If any candidate is AMBIGUOUS, priority goes to manual review
            ambiguous_candidates = [d for d in candidates if d.status == ExtractionStatus.AMBIGUOUS]
            if ambiguous_candidates:
                target_decl = ambiguous_candidates[0]
            else:
                target_decl = max(candidates, key=lambda d: d.confidence)
            field_name = target_decl.declaration_type.value

        evidence = self.create_evidence_references(target_decl, field_name)
        inputs_used.update({
            "selected_entity_type": field_name,
            "entity_value": target_decl.value,
            "confidence": target_decl.confidence,
            "status": target_decl.status.value,
        })

        # 3. Ambiguity Resolution
        if target_decl.status == ExtractionStatus.AMBIGUOUS:
            return self.review_finding(
                explanation=(
                    f"Ambiguous {field_name} declaration: Multiple conflicting entity details detected ({target_decl.notes or ''}). "
                    f"Manual review required under Rule 6(1)(a)."
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
                    f"{field_name} details '{val_str}' were detected with low confidence ({target_decl.confidence:.2f}). "
                    f"Manual review required to verify complete address."
                ),
                input_values_used=inputs_used,
                evidence_references=evidence,
                confidence=target_decl.confidence,
            )

        # 5. Meaningful content check (malformed / incomplete)
        if len(val_str) < 4 or val_str.lower() in ("n/a", "none", "null", "address"):
            return self.fail_finding(
                explanation=f"Malformed or incomplete {field_name} declaration: '{val_str}'.",
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
