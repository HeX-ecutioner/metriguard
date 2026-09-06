import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.models import Inspection, PackageImage, Declaration, Violation, InspectionResult
from app.db.crud import create_inspection_record, get_inspection_record, list_inspection_records
from app.core.config import BACKEND_DIR, settings


def test_isolated_sqlite_database(tmp_path):
    """
    Verifies SQLite foundation in complete isolation:
    1. Creates a temporary SQLite database
    2. Creates all required tables
    3. Inserts a record using CRUD layer
    4. Retrieves and verifies the record and relations
    5. Confirms the dev database is untouched
    6. Properly disposes engine and isolates the temp database
    """
    # 1. Temporary SQLite database path
    temp_db_path = tmp_path / "test_isolated.db"
    temp_db_url = f"sqlite:///{temp_db_path.as_posix()}"

    test_engine = create_engine(
        temp_db_url,
        connect_args={"check_same_thread": False},
        echo=False
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    try:
        # 2. Create required tables
        Base.metadata.create_all(bind=test_engine)
        assert temp_db_path.exists(), "Temporary database file was not created."

        # 3. Insert a record via CRUD layer
        with TestSession() as session:
            record = create_inspection_record(
                db=session,
                status="COMPLIANT",
                confidence_score=0.97,
                extracted_texts=[
                    {"text": "MRP Rs. 150", "confidence": 0.98},
                    {"text": "Net Wt 500g", "confidence": 0.95}
                ],
                violations=[],
                image_path="test_package_001.jpg"
            )
            assert record.id is not None
            record_id = record.id

        # 4. Retrieve record from temporary database
        with TestSession() as session:
            retrieved = get_inspection_record(db=session, record_id=record_id)
            assert retrieved is not None
            assert retrieved.id == record_id
            assert retrieved.status == "COMPLIANT"
            assert retrieved.overall_confidence == 0.97
            assert len(retrieved.declarations) == 2
            assert any("MRP Rs. 150" in d.extracted_value for d in retrieved.declarations)
            assert len(retrieved.images) == 1
            assert retrieved.images[0].file_path == "test_package_001.jpg"
            assert retrieved.result is not None

            # Check list function
            records = list_inspection_records(db=session, skip=0, limit=10)
            assert len(records) == 1
            assert records[0].id == record_id

        # 5. Verify development database is not modified
        dev_db_path = Path(settings.get_resolved_database_url().replace("sqlite:///", ""))
        if dev_db_path.exists():
            from app.db.database import SessionLocal
            with SessionLocal() as dev_session:
                # The record inserted in temp_db should NOT exist in dev_db with this test payload
                dev_record = dev_session.query(PackageImage).filter(
                    PackageImage.file_path == "test_package_001.jpg"
                ).first()
                assert dev_record is None, "Development database was modified by test!"

    finally:
        # 6. Dispose engine to release file lock on Windows
        test_engine.dispose()
