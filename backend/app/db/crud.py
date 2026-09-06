"""
Database CRUD operations for MetriGuard inspection workflow entities.
Encapsulates database queries and transactions so route handlers do not contain direct SQL/ORM logic.
"""

import json
from typing import List, Optional, Any, Dict
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.db.models import (
    Inspection,
    PackageImage,
    Declaration,
    Violation,
    InspectionResult,
    InspectionStatus,
    ViolationSeverity,
)


def create_inspection(
    db: Session,
    status: InspectionStatus = InspectionStatus.CREATED,
    product_name: Optional[str] = None,
    overall_confidence: Optional[float] = None,
    notes: Optional[str] = None
) -> Inspection:
    """Creates a new commodity inspection session."""
    inspection = Inspection(
        status=status,
        product_name=product_name,
        overall_confidence=overall_confidence,
        notes=notes
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


def get_inspection(db: Session, inspection_id: int) -> Optional[Inspection]:
    """Retrieves an inspection session by ID, eagerly loading all related entities."""
    return (
        db.query(Inspection)
        .options(
            joinedload(Inspection.images),
            joinedload(Inspection.declarations),
            joinedload(Inspection.violations),
            joinedload(Inspection.result),
        )
        .filter(Inspection.id == inspection_id)
        .first()
    )


def list_inspections(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    search: Optional[str] = None
) -> List[Inspection]:
    """Retrieves paginated inspection sessions with eager loading and optional filtering."""
    query = (
        db.query(Inspection)
        .options(
            joinedload(Inspection.images),
            joinedload(Inspection.declarations),
            joinedload(Inspection.violations),
            joinedload(Inspection.result),
        )
    )
    if status_filter:
        try:
            enum_val = InspectionStatus(status_filter.upper())
            query = query.filter(Inspection.status == enum_val)
        except ValueError:
            pass

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Inspection.product_name.ilike(search_pattern)) |
            (Inspection.notes.ilike(search_pattern))
        )

    return (
        query.order_by(Inspection.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )



def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    """Calculates real-time inspection metrics and top violations directly from SQLite."""
    total_inspections = db.query(func.count(Inspection.id)).scalar() or 0
    compliant_count = (
        db.query(func.count(Inspection.id))
        .filter(Inspection.status == InspectionStatus.COMPLIANT)
        .scalar()
        or 0
    )
    non_compliant_count = (
        db.query(func.count(Inspection.id))
        .filter(Inspection.status == InspectionStatus.NON_COMPLIANT)
        .scalar()
        or 0
    )
    manual_review_count = (
        db.query(func.count(Inspection.id))
        .filter(Inspection.status == InspectionStatus.MANUAL_REVIEW)
        .scalar()
        or 0
    )

    # Top violations: group by rule_id, title, severity, order by count desc, limit 5
    violation_rows = (
        db.query(
            Violation.rule_id,
            Violation.title,
            Violation.severity,
            func.count(Violation.id).label("count")
        )
        .group_by(Violation.rule_id, Violation.title, Violation.severity)
        .order_by(func.count(Violation.id).desc())
        .limit(5)
        .all()
    )

    top_violations = [
        {
            "rule_id": row.rule_id,
            "title": row.title,
            "severity": row.severity.value if hasattr(row.severity, "value") else str(row.severity),
            "count": row.count,
        }
        for row in violation_rows
    ]

    recent_inspections = list_inspections(db, skip=0, limit=10)

    return {
        "total_inspections": total_inspections,
        "compliant_inspections": compliant_count,
        "non_compliant_inspections": non_compliant_count,
        "manual_review_inspections": manual_review_count,
        "top_violations": top_violations,
        "recent_inspections": recent_inspections,
    }



def update_inspection_status(
    db: Session,
    inspection_id: int,
    status: InspectionStatus,
    overall_confidence: Optional[float] = None
) -> Optional[Inspection]:
    """Updates status and confidence score of an inspection."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        return None
    inspection.status = status
    if overall_confidence is not None:
        inspection.overall_confidence = overall_confidence
    db.commit()
    db.refresh(inspection)
    return inspection


def add_package_image(
    db: Session,
    inspection_id: int,
    file_path: str,
    original_filename: str,
    mime_type: str = "image/jpeg",
    file_size: int = 0,
    width: Optional[int] = None,
    height: Optional[int] = None
) -> PackageImage:
    """Attaches a package image to an inspection session."""
    image = PackageImage(
        inspection_id=inspection_id,
        file_path=file_path,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
        width=width,
        height=height
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def add_declaration(
    db: Session,
    inspection_id: int,
    declaration_type: str,
    extracted_value: str,
    confidence: Optional[float] = None,
    source_image_id: Optional[int] = None,
    bounding_box: Optional[Dict[str, Any]] = None
) -> Declaration:
    """Attaches an extracted package declaration to an inspection session."""
    bbox_str = json.dumps(bounding_box) if bounding_box is not None else None
    declaration = Declaration(
        inspection_id=inspection_id,
        declaration_type=declaration_type,
        extracted_value=extracted_value,
        confidence=confidence,
        source_image_id=source_image_id,
        bounding_box=bbox_str
    )
    db.add(declaration)
    db.commit()
    db.refresh(declaration)
    return declaration


def add_violation(
    db: Session,
    inspection_id: int,
    rule_id: str,
    title: str,
    explanation: str,
    severity: ViolationSeverity = ViolationSeverity.ERROR,
    rule_version: str = "2011",
    confidence: Optional[float] = None,
    evidence_image_id: Optional[int] = None,
    evidence_bounding_box: Optional[Dict[str, Any]] = None,
    measured_value: Optional[str] = None,
    expected_value: Optional[str] = None
) -> Violation:
    """Records a traceable compliance violation with rule reference and evidence."""
    bbox_str = json.dumps(evidence_bounding_box) if evidence_bounding_box is not None else None
    violation = Violation(
        inspection_id=inspection_id,
        rule_id=rule_id,
        rule_version=rule_version,
        title=title,
        explanation=explanation,
        severity=severity,
        confidence=confidence,
        evidence_image_id=evidence_image_id,
        evidence_bounding_box=bbox_str,
        measured_value=measured_value,
        expected_value=expected_value
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)
    return violation


def set_inspection_result(
    db: Session,
    inspection_id: int,
    final_status: InspectionStatus,
    summary: str
) -> InspectionResult:
    """Records or updates the synthesized regulatory result for an inspection."""
    existing = db.query(InspectionResult).filter(InspectionResult.inspection_id == inspection_id).first()
    if existing:
        existing.final_status = final_status
        existing.summary = summary
        db.commit()
        db.refresh(existing)
        return existing

    result = InspectionResult(
        inspection_id=inspection_id,
        final_status=final_status,
        summary=summary
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def create_inspection_record(
    db: Session,
    status: str,
    confidence_score: float,
    extracted_texts: List[Any],
    violations: List[Any],
    image_path: Optional[str] = None
) -> Inspection:
    """
    Workflow orchestrator: persists an inspection and populates all 5 relational models:
    - Inspection
    - PackageImage
    - Declarations (from extracted_texts)
    - Violations (from violations list)
    - InspectionResult (synthesized summary)
    """
    # Normalize status to InspectionStatus enum
    try:
        inspection_status = InspectionStatus(status)
    except (ValueError, KeyError):
        inspection_status = InspectionStatus.MANUAL_REVIEW

    # 1. Create main Inspection entity
    inspection = Inspection(
        status=inspection_status,
        overall_confidence=confidence_score,
        notes=f"Processed with {len(violations)} violations and {len(extracted_texts)} declarations"
    )
    db.add(inspection)
    db.flush()

    # 2. Add PackageImage if image_path is present
    image_id = None
    if image_path:
        filename = image_path.split("/")[-1] if "/" in image_path else image_path
        package_img = PackageImage(
            inspection_id=inspection.id,
            file_path=image_path,
            original_filename=filename,
            mime_type="image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png",
            file_size=0
        )
        db.add(package_img)
        db.flush()
        image_id = package_img.id

    # 3. Add Declarations
    for item in extracted_texts:
        text_val = item.get("text", "") if isinstance(item, dict) else str(item)
        conf = item.get("confidence") if isinstance(item, dict) else None
        bbox = item.get("box") if isinstance(item, dict) else None

        decl = Declaration(
            inspection_id=inspection.id,
            declaration_type="extracted_text",
            extracted_value=text_val,
            confidence=conf,
            source_image_id=image_id,
            bounding_box=json.dumps(bbox) if bbox else None
        )
        db.add(decl)

    # 4. Add Violations
    for v in violations:
        if isinstance(v, dict):
            rule_id = v.get("rule_id", "LEGAL_METROLOGY_RULE")
            rule_version = v.get("rule_version", "2011")
            title = v.get("rule_name", v.get("title", "Compliance Violation"))
            explanation = v.get("description", v.get("explanation", "Violation of packaged commodity rules"))
            severity_str = v.get("severity", "ERROR")
            try:
                severity = ViolationSeverity(severity_str)
            except ValueError:
                severity = ViolationSeverity.ERROR
        else:
            rule_id = getattr(v, "rule_id", "LEGAL_METROLOGY_RULE")
            rule_version = getattr(v, "rule_version", "2011")
            title = getattr(v, "rule_name", getattr(v, "title", "Compliance Violation"))
            explanation = getattr(v, "description", getattr(v, "explanation", "Violation"))
            severity_str = getattr(v, "severity", "ERROR")
            try:
                severity = ViolationSeverity(severity_str)
            except ValueError:
                severity = ViolationSeverity.ERROR

        violation = Violation(
            inspection_id=inspection.id,
            rule_id=rule_id,
            rule_version=rule_version,
            title=title,
            explanation=explanation,
            severity=severity,
            confidence=confidence_score,
            evidence_image_id=image_id
        )
        db.add(violation)

    # 5. Add InspectionResult
    summary = f"Inspection completed with status {inspection_status.value}. Detected {len(violations)} violations."
    res = InspectionResult(
        inspection_id=inspection.id,
        final_status=inspection_status,
        summary=summary
    )
    db.add(res)

    db.commit()
    db.refresh(inspection)
    return inspection


def get_inspection_record(db: Session, record_id: int) -> Optional[Inspection]:
    """Compatibility getter for Inspection entity."""
    return get_inspection(db, record_id)


def list_inspection_records(db: Session, skip: int = 0, limit: int = 100) -> List[Inspection]:
    """Compatibility lister for Inspection entities."""
    return list_inspections(db, skip, limit)
