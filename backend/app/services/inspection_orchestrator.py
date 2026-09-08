"""
Inspection Orchestrator Service for MetriGuard.
Coordinates the end-to-end Legal Metrology inspection workflow:
1. Validates and decodes uploaded package images
2. Securely stores images and records metadata in database
3. Dispatches OCR processing via OCRService (failures routed strictly to MANUAL_REVIEW)
4. Extracts structured declarations across 13 Legal Metrology declaration types
5. Executes deterministic regulatory rule evaluation
6. Persists declarations, violations, and synthesized outcomes in SQLite
7. Returns complete inspection outcome to caller
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Inspection,
    PackageImage,
    InspectionStatus,
    ViolationSeverity,
)
from app.db.crud import (
    get_inspection,
    add_package_image,
    add_declaration,
    add_violation,
    set_inspection_result,
    update_inspection_status,
)
from app.models.schemas import (
    PackageImageResponse,
    RuleViolation,
    Evidence,
    BoundingBox,
)
from app.models.declaration_schemas import (
    DeclarationType,
    ExtractionStatus,
    DeclarationExtractionResult,
)
from app.models.ocr_schemas import OCRResult, OCRError
from app.services.image_validator import validate_and_decode_image, ImageValidationError
from app.services.storage import get_storage_service, StorageService, StorageError
from app.services.ocr.service import OCRService
from app.services.extraction.extractor import DeclarationExtractor
from app.services.rules.engine import RuleEngine
from app.services.rules.models import (
    RuleResult,
    RuleSeverity,
    ComplianceEvaluationResult,
)

logger = logging.getLogger(__name__)


def map_rule_severity(severity: RuleSeverity) -> ViolationSeverity:
    """Maps rule engine severity classifications to database ViolationSeverity enums."""
    mapping = {
        RuleSeverity.CRITICAL: ViolationSeverity.CRITICAL,
        RuleSeverity.ERROR: ViolationSeverity.ERROR,
        RuleSeverity.WARNING: ViolationSeverity.WARNING,
        RuleSeverity.INFO: ViolationSeverity.INFO,
    }
    return mapping.get(severity, ViolationSeverity.ERROR)


class InspectionOrchestrator:
    """
    Dedicated orchestration service separating inspection lifecycle workflow
    from HTTP route handlers. Supports dependency injection for automated testing.
    """

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
        declaration_extractor: Optional[DeclarationExtractor] = None,
        rule_engine: Optional[RuleEngine] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.ocr_service = ocr_service or OCRService()
        self.declaration_extractor = declaration_extractor or DeclarationExtractor()
        self.rule_engine = rule_engine or RuleEngine()
        self.storage_service = storage_service or get_storage_service()

    async def process_image_upload(
        self,
        db: Session,
        inspection_id: int,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        package_type: str = "retail",
        commodity_category: Optional[str] = None,
        is_imported: bool = False,
    ) -> PackageImageResponse:
        """
        Executes the complete inspection pipeline for an uploaded package image.

        Guarantees:
        - OCR failure never becomes COMPLIANT (routes strictly to MANUAL_REVIEW).
        - Rule engine failures route to MANUAL_REVIEW.
        - Low-confidence extractions or ambiguous values route to MANUAL_REVIEW.
        - All declarations, violations, and results are persisted in SQLite.
        """
        # 1. Verify inspection session exists and is eligible for upload
        inspection = get_inspection(db=db, inspection_id=inspection_id)
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inspection with ID {inspection_id} not found."
            )

        # Core Business Invariant: Exactly one image per inspection session.
        # An inspection session must never contain multiple uploaded images.
        if inspection.images and len(inspection.images) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inspection session {inspection_id} already contains an uploaded image. Each inspection session allows exactly one image."
            )

        if inspection.status != InspectionStatus.CREATED:
            status_str = inspection.status.value if hasattr(inspection.status, "value") else str(inspection.status)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inspection session {inspection_id} is in status '{status_str}' and cannot accept new images. Each inspection session allows exactly one image."
            )

        # 2. Validate and decode image (rejects bad payload with 400/413/415 without corrupting session)
        try:
            validated = validate_and_decode_image(
                content=file_bytes,
                original_filename=filename,
                content_type=content_type,
                max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
            )
        except ImageValidationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)

        # Transition status to PROCESSING now that image is valid
        update_inspection_status(
            db=db,
            inspection_id=inspection_id,
            status=InspectionStatus.PROCESSING,
        )

        # 3. Securely store image in local storage
        safe_original = Path(filename).name or "uploaded_package.jpg"
        try:
            file_key = await self.storage_service.save_file(
                filename=safe_original,
                content=file_bytes
            )
        except StorageError as se:
            logger.error(f"Storage failure for inspection {inspection_id}: {se.detail}")
            update_inspection_status(db=db, inspection_id=inspection_id, status=InspectionStatus.FAILED)
            raise HTTPException(status_code=se.status_code, detail=se.detail)

        # 4. Record PackageImage metadata in database (enforcing single image constraint)
        from sqlalchemy.exc import IntegrityError
        try:
            package_image = add_package_image(
                db=db,
                inspection_id=inspection_id,
                file_path=file_key,
                original_filename=safe_original,
                mime_type=validated.mime_type,
                file_size=validated.file_size,
                width=validated.width,
                height=validated.height,
            )
        except IntegrityError as ie:
            db.rollback()
            await self.storage_service.delete_file(file_key)
            logger.warning(f"Integrity violation adding image to inspection {inspection_id}: {ie}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inspection session {inspection_id} already has an attached image."
            )
        except Exception as db_err:
            db.rollback()
            logger.error(f"Failed to record image metadata in DB: {db_err}")
            await self.storage_service.delete_file(file_key)
            update_inspection_status(db=db, inspection_id=inspection_id, status=InspectionStatus.FAILED)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record image metadata in database."
            )

        # Prepare default image URL
        image_url = f"/api/v1/inspections/{inspection_id}/images/{package_image.id}/file"

        # 5. Execute OCR Processing
        ocr_result: Optional[OCRResult] = None
        ocr_failed = False
        ocr_failure_reason = ""

        try:
            ocr_result = self.ocr_service.process_image(
                image_input=file_bytes,
                image_id=package_image.id,
                inspection_id=inspection_id,
                db=db,
            )
        except Exception as ocr_err:
            logger.error(f"OCR processing failed for image {package_image.id}: {ocr_err}")
            ocr_failed = True
            ocr_failure_reason = str(ocr_err)

        # CRITICAL SAFETY GUARANTEE: OCR failure must NOT become COMPLIANT.
        if ocr_failed or ocr_result is None:
            status_enum = InspectionStatus.MANUAL_REVIEW
            summary = f"OCR processing failed: {ocr_failure_reason or 'Image could not be read'}. Requires manual review."
            set_inspection_result(
                db=db,
                inspection_id=inspection_id,
                final_status=status_enum,
                summary=summary,
            )
            update_inspection_status(
                db=db,
                inspection_id=inspection_id,
                status=status_enum,
                overall_confidence=0.0,
            )
            return PackageImageResponse(
                id=package_image.id,
                inspection_id=package_image.inspection_id,
                file_path=package_image.file_path,
                original_filename=package_image.original_filename,
                mime_type=package_image.mime_type,
                file_size=package_image.file_size,
                width=package_image.width,
                height=package_image.height,
                created_at=package_image.created_at,
                status=status_enum.value,
                confidence_score=0.0,
                extracted_texts=[],
                violations=[],
                image_url=image_url,
            )

        # CRITICAL SAFETY GUARANTEE: Empty OCR text (non-package image, extreme blur/glare)
        # must NOT automatically become NON_COMPLIANT due to missing evidence.
        if not ocr_result.items:
            status_enum = InspectionStatus.MANUAL_REVIEW
            summary = "No legible text or declarations detected on the uploaded image. Requires manual officer inspection."
            set_inspection_result(
                db=db,
                inspection_id=inspection_id,
                final_status=status_enum,
                summary=summary,
            )
            update_inspection_status(
                db=db,
                inspection_id=inspection_id,
                status=status_enum,
                overall_confidence=0.0,
            )
            return PackageImageResponse(
                id=package_image.id,
                inspection_id=package_image.inspection_id,
                file_path=package_image.file_path,
                original_filename=package_image.original_filename,
                mime_type=package_image.mime_type,
                file_size=package_image.file_size,
                width=package_image.width,
                height=package_image.height,
                created_at=package_image.created_at,
                status=status_enum.value,
                confidence_score=0.0,
                extracted_texts=[],
                violations=[],
                image_url=image_url,
            )

        # 6. Extract Structured Declarations
        try:
            extraction_result: DeclarationExtractionResult = self.declaration_extractor.extract_from_ocr(
                ocr_input=ocr_result,
                image_id=package_image.id
            )
        except Exception as extract_err:
            logger.error(f"Declaration extraction failure: {extract_err}")
            extraction_result = DeclarationExtractionResult(
                image_id=package_image.id,
                declarations={},
                all_candidates=[],
                summary={},
                has_ambiguities=True
            )

        # Persist extracted declarations into database
        extracted_texts_summary: List[str] = []
        for decl_type, decl in extraction_result.declarations.items():
            if decl.status != ExtractionStatus.MISSING and decl.value:
                bbox_dict = decl.bounding_box.model_dump() if decl.bounding_box else None

                add_declaration(
                    db=db,
                    inspection_id=inspection_id,
                    declaration_type=decl_type.value,
                    extracted_value=decl.value,
                    confidence=decl.confidence,
                    source_image_id=package_image.id,
                    bounding_box=bbox_dict,
                )
                extracted_texts_summary.append(f"{decl_type.value}: {decl.value}")

        # If no structured declarations detected, record raw recognized lines
        if not extracted_texts_summary and ocr_result.recognized_text:
            for line in ocr_result.recognized_text.splitlines():
                clean_line = line.strip()
                if clean_line:
                    extracted_texts_summary.append(clean_line)

        # 7. Evaluate Deterministic Rule Engine
        rule_eval_failed = False
        rule_eval_failure_reason = ""
        compliance_result: Optional[ComplianceEvaluationResult] = None

        try:
            compliance_result = self.rule_engine.evaluate_extraction(
                extraction_result=extraction_result,
                package_type=package_type,
                commodity_category=commodity_category,
                is_imported=is_imported,
            )
        except Exception as rule_err:
            logger.error(f"Rule engine evaluation failed: {rule_err}")
            rule_eval_failed = True
            rule_eval_failure_reason = str(rule_err)

        if rule_eval_failed or compliance_result is None:
            status_enum = InspectionStatus.MANUAL_REVIEW
            summary = f"Rule engine evaluation failed: {rule_eval_failure_reason or 'Engine error'}. Requires manual inspection."
            set_inspection_result(
                db=db,
                inspection_id=inspection_id,
                final_status=status_enum,
                summary=summary,
            )
            update_inspection_status(
                db=db,
                inspection_id=inspection_id,
                status=status_enum,
                overall_confidence=0.5,
            )
            return PackageImageResponse(
                id=package_image.id,
                inspection_id=package_image.inspection_id,
                file_path=package_image.file_path,
                original_filename=package_image.original_filename,
                mime_type=package_image.mime_type,
                file_size=package_image.file_size,
                width=package_image.width,
                height=package_image.height,
                created_at=package_image.created_at,
                status=status_enum.value,
                confidence_score=0.5,
                extracted_texts=extracted_texts_summary,
                violations=[],
                image_url=image_url,
            )

        # 8. Synthesize Status & Persist Findings
        # Determine status enum
        res_status = compliance_result.overall_status.upper()
        if ocr_result.is_low_confidence:
            # CRITICAL SAFETY GUARANTEE: Low OCR confidence / text uncertainty must NOT
            # automatically become NON_COMPLIANT due to missing evidence.
            status_enum = InspectionStatus.MANUAL_REVIEW
        elif res_status == "COMPLIANT":
            status_enum = InspectionStatus.COMPLIANT
        elif res_status == "NON_COMPLIANT":
            status_enum = InspectionStatus.NON_COMPLIANT
        else:
            status_enum = InspectionStatus.MANUAL_REVIEW

        # Persist violations
        response_violations: List[RuleViolation] = []
        for finding in compliance_result.findings:
            if finding.result == RuleResult.FAIL:
                bbox_dict = None
                if finding.evidence_references and finding.evidence_references[0].bounding_box:
                    bbox_dict = finding.evidence_references[0].bounding_box

                measured_val = None
                for k in ["mrp_value", "net_quantity", "entity_name", "date_value", "usp_value"]:
                    if k in finding.input_values_used:
                        measured_val = str(finding.input_values_used[k])
                        break

                expected_val = None
                if "expected_unit" in finding.input_values_used:
                    expected_val = str(finding.input_values_used["expected_unit"])

                add_violation(
                    db=db,
                    inspection_id=inspection_id,
                    rule_id=finding.rule_id,
                    rule_version=finding.rule_version,
                    title=finding.rule_id,
                    explanation=finding.explanation,
                    severity=map_rule_severity(finding.severity),
                    confidence=finding.confidence,
                    evidence_image_id=package_image.id,
                    evidence_bounding_box=bbox_dict,
                    measured_value=measured_val,
                    expected_value=expected_val,
                )

                ev = None
                if bbox_dict:
                    ev = Evidence(
                        text=finding.explanation,
                        box=BoundingBox(
                            x=bbox_dict.get("x", 0),
                            y=bbox_dict.get("y", 0),
                            width=bbox_dict.get("width", 0),
                            height=bbox_dict.get("height", 0)
                        ),
                        confidence=finding.confidence
                    )

                response_violations.append(
                    RuleViolation(
                        rule_id=finding.rule_id,
                        explanation=finding.explanation,
                        confidence=finding.confidence,
                        evidence=ev,
                    )
                )

        # Calculate overall confidence score:
        # Weighted combination of OCR confidence and rule confidence
        calc_confidence = round(
            min(1.0, max(0.1, (ocr_result.confidence * 0.5) + (1.0 if status_enum == InspectionStatus.COMPLIANT else 0.8) * 0.5)),
            2
        )
        if status_enum == InspectionStatus.MANUAL_REVIEW:
            calc_confidence = min(calc_confidence, 0.65)

        # Persist synthesized summary
        if ocr_result.is_low_confidence:
            summary_text = (
                f"Inspection routed to MANUAL_REVIEW. Optical recognition confidence ({ocr_result.confidence * 100:.1f}%) "
                f"is below threshold ({self.ocr_service.confidence_threshold * 100:.1f}%). "
                f"Declarations could not be verified with automated certainty; physical package inspection required."
            )
        else:
            summary_text = (
                f"Inspection completed with status {status_enum.value}. "
                f"Evaluated {len(compliance_result.findings)} rules: "
                f"{compliance_result.summary.get('PASS', 0)} passed, "
                f"{compliance_result.summary.get('FAIL', 0)} failed, "
                f"{compliance_result.summary.get('REVIEW', 0)} review required, "
                f"{compliance_result.summary.get('NOT_APPLICABLE', 0)} not applicable."
            )

        set_inspection_result(
            db=db,
            inspection_id=inspection_id,
            final_status=status_enum,
            summary=summary_text,
        )

        update_inspection_status(
            db=db,
            inspection_id=inspection_id,
            status=status_enum,
            overall_confidence=calc_confidence,
        )

        return PackageImageResponse(
            id=package_image.id,
            inspection_id=package_image.inspection_id,
            file_path=package_image.file_path,
            original_filename=package_image.original_filename,
            mime_type=package_image.mime_type,
            file_size=package_image.file_size,
            width=package_image.width,
            height=package_image.height,
            created_at=package_image.created_at,
            status=status_enum.value,
            confidence_score=calc_confidence,
            extracted_texts=extracted_texts_summary,
            violations=response_violations,
            image_url=image_url,
        )


def get_inspection_orchestrator() -> InspectionOrchestrator:
    """Dependency provider for FastAPI route injection."""
    return InspectionOrchestrator()
