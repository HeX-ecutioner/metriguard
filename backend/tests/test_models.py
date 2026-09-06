import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.models import (
    Inspection,
    PackageImage,
    Declaration,
    Violation,
    InspectionResult,
    InspectionStatus,
    ViolationSeverity,
)
from app.db.crud import (
    create_inspection,
    add_package_image,
    add_declaration,
    add_violation,
    set_inspection_result,
    get_inspection,
)


@pytest.fixture
def db_session(tmp_path):
    """Provides an isolated SQLite database session with foreign key support enabled."""
    db_file = tmp_path / "test_models.db"
    engine = create_engine(
        f"sqlite:///{db_file.as_posix()}",
        connect_args={"check_same_thread": False},
        echo=False
    )
    # Enable SQLite foreign keys
    from sqlite3 import Connection as SQLite3Connection
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_full_inspection_workflow(db_session):
    """
    Verifies that all 5 entities can be created, linked, and retrieved
    with full relationship navigation.
    """
    # 1. Create Inspection
    inspection = create_inspection(
        db=db_session,
        status=InspectionStatus.PROCESSING,
        product_name="Atta Whole Wheat Flour 5kg",
        overall_confidence=0.96,
        notes="Automated inspection batch test"
    )
    assert inspection.id is not None
    assert inspection.status == InspectionStatus.PROCESSING
    assert inspection.created_at is not None
    assert inspection.updated_at is not None

    # 2. Attach PackageImage
    image = add_package_image(
        db=db_session,
        inspection_id=inspection.id,
        file_path="uploads/wheat_front_label.jpg",
        original_filename="wheat_front_label.jpg",
        mime_type="image/jpeg",
        file_size=1048576,
        width=1920,
        height=1080
    )
    assert image.id is not None
    assert image.inspection_id == inspection.id

    # 3. Attach Declarations
    decl_mrp = add_declaration(
        db=db_session,
        inspection_id=inspection.id,
        declaration_type="mrp",
        extracted_value="Rs. 240.00 (incl. of all taxes)",
        confidence=0.98,
        source_image_id=image.id,
        bounding_box={"x": 100, "y": 200, "w": 300, "h": 50}
    )
    decl_net_qty = add_declaration(
        db=db_session,
        inspection_id=inspection.id,
        declaration_type="net_quantity",
        extracted_value="5 kg",
        confidence=0.99,
        source_image_id=image.id,
        bounding_box={"x": 100, "y": 260, "w": 150, "h": 40}
    )
    assert decl_mrp.id is not None
    assert decl_net_qty.id is not None

    # 4. Attach Traceable Violation
    violation = add_violation(
        db=db_session,
        inspection_id=inspection.id,
        rule_id="RULE_6_1_D_DATE",
        title="Date of Manufacture Missing",
        explanation="Package fails to declare month and year of manufacture or packing.",
        severity=ViolationSeverity.ERROR,
        rule_version="2011",
        confidence=0.95,
        evidence_image_id=image.id,
        evidence_bounding_box={"x": 50, "y": 50, "w": 400, "h": 500},
        measured_value=None,
        expected_value="MM/YYYY or Month, Year"
    )
    assert violation.id is not None
    assert violation.rule_id == "RULE_6_1_D_DATE"
    assert violation.rule_version == "2011"
    assert violation.severity == ViolationSeverity.ERROR

    # 5. Attach InspectionResult
    result = set_inspection_result(
        db=db_session,
        inspection_id=inspection.id,
        final_status=InspectionStatus.NON_COMPLIANT,
        summary="Inspection completed: 1 mandatory declaration violation detected."
    )
    assert result.id is not None
    assert result.final_status == InspectionStatus.NON_COMPLIANT

    # 6. Verify full eager loading and relationships
    retrieved = get_inspection(db=db_session, inspection_id=inspection.id)
    assert retrieved is not None
    assert len(retrieved.images) == 1
    assert retrieved.images[0].original_filename == "wheat_front_label.jpg"
    assert len(retrieved.declarations) == 2
    assert len(retrieved.violations) == 1
    assert retrieved.violations[0].title == "Date of Manufacture Missing"
    assert retrieved.result is not None
    assert retrieved.result.final_status == InspectionStatus.NON_COMPLIANT


def test_cascade_delete_inspection(db_session):
    """
    Verifies that deleting an Inspection cascades and removes all dependent child
    records (PackageImage, Declaration, Violation, InspectionResult).
    """
    inspection = create_inspection(db=db_session, status=InspectionStatus.CREATED)
    img = add_package_image(
        db=db_session,
        inspection_id=inspection.id,
        file_path="uploads/label.jpg",
        original_filename="label.jpg"
    )
    decl = add_declaration(
        db=db_session,
        inspection_id=inspection.id,
        declaration_type="mrp",
        extracted_value="100",
        source_image_id=img.id
    )
    viol = add_violation(
        db=db_session,
        inspection_id=inspection.id,
        rule_id="RULE_TEST",
        title="Test Violation",
        explanation="Explanation",
        evidence_image_id=img.id
    )
    res = set_inspection_result(
        db=db_session,
        inspection_id=inspection.id,
        final_status=InspectionStatus.FAILED,
        summary="Failed"
    )

    insp_id = inspection.id
    img_id = img.id
    decl_id = decl.id
    viol_id = viol.id
    res_id = res.id

    # Delete the inspection root entity
    db_session.delete(inspection)
    db_session.commit()

    # All related entities must be cascade-deleted
    assert db_session.query(Inspection).filter(Inspection.id == insp_id).first() is None
    assert db_session.query(PackageImage).filter(PackageImage.id == img_id).first() is None
    assert db_session.query(Declaration).filter(Declaration.id == decl_id).first() is None
    assert db_session.query(Violation).filter(Violation.id == viol_id).first() is None
    assert db_session.query(InspectionResult).filter(InspectionResult.id == res_id).first() is None


def test_package_image_deletion_sets_null(db_session):
    """
    Verifies that deleting a PackageImage nullifies foreign keys in declarations
    and violations (SET NULL) instead of cascading deletion to them.
    """
    inspection = create_inspection(db=db_session, status=InspectionStatus.PROCESSING)
    img = add_package_image(
        db=db_session,
        inspection_id=inspection.id,
        file_path="uploads/sample.png",
        original_filename="sample.png"
    )
    decl = add_declaration(
        db=db_session,
        inspection_id=inspection.id,
        declaration_type="net_qty",
        extracted_value="1 kg",
        source_image_id=img.id
    )
    viol = add_violation(
        db=db_session,
        inspection_id=inspection.id,
        rule_id="RULE_TEST",
        title="Test",
        explanation="Test",
        evidence_image_id=img.id
    )

    # Delete image only
    db_session.delete(img)
    db_session.commit()

    db_session.refresh(decl)
    db_session.refresh(viol)
    # FKs must be set to None (SET NULL)
    assert decl.source_image_id is None
    assert viol.evidence_image_id is None
    # Declaration and Violation remain preserved
    assert decl.extracted_value == "1 kg"
    assert viol.title == "Test"


def test_low_confidence_declaration_is_not_a_violation(db_session):
    """
    Design Rule: A low-confidence extraction must NOT automatically become a violation.
    An inspection can contain low-confidence declarations without violations.
    """
    inspection = create_inspection(db=db_session, status=InspectionStatus.MANUAL_REVIEW)

    # Low confidence extraction (e.g. OCR unreadable or blurry text)
    decl = add_declaration(
        db=db_session,
        inspection_id=inspection.id,
        declaration_type="mrp",
        extracted_value="Rs. ???",
        confidence=0.25
    )

    # Status is MANUAL_REVIEW, but no violations exist automatically
    result = set_inspection_result(
        db=db_session,
        inspection_id=inspection.id,
        final_status=InspectionStatus.MANUAL_REVIEW,
        summary="Low OCR confidence requires manual inspector verification."
    )

    retrieved = get_inspection(db=db_session, inspection_id=inspection.id)
    assert len(retrieved.declarations) == 1
    assert retrieved.declarations[0].confidence == 0.25
    assert len(retrieved.violations) == 0
    assert retrieved.result.final_status == InspectionStatus.MANUAL_REVIEW


def test_violation_traceability_to_rule(db_session):
    """
    Design Rule: Every violation must be traceable to a specific rule and version.
    """
    inspection = create_inspection(db=db_session, status=InspectionStatus.PROCESSING)
    violation = add_violation(
        db=db_session,
        inspection_id=inspection.id,
        rule_id="RULE_6_1_E_RETAIL_PRICE",
        rule_version="2011_AMENDMENT_2022",
        title="MRP Declaration Missing",
        explanation="Package lacks mandatory Maximum Retail Price declaration.",
        severity=ViolationSeverity.CRITICAL,
        confidence=0.99,
        measured_value=None,
        expected_value="MRP Rs. XX.XX (incl. of all taxes)"
    )

    assert violation.rule_id == "RULE_6_1_E_RETAIL_PRICE"
    assert violation.rule_version == "2011_AMENDMENT_2022"
    assert violation.severity == ViolationSeverity.CRITICAL


def test_all_enum_values():
    """Validates defined values for InspectionStatus and ViolationSeverity enums."""
    assert set(InspectionStatus) == {
        InspectionStatus.CREATED,
        InspectionStatus.PROCESSING,
        InspectionStatus.COMPLIANT,
        InspectionStatus.NON_COMPLIANT,
        InspectionStatus.MANUAL_REVIEW,
        InspectionStatus.FAILED,
    }
    assert set(ViolationSeverity) == {
        ViolationSeverity.INFO,
        ViolationSeverity.WARNING,
        ViolationSeverity.ERROR,
        ViolationSeverity.CRITICAL,
    }
