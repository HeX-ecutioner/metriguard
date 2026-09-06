"""
Database CRUD operations for MetriGuard.
Encapsulates database queries and transactions so route handlers do not contain direct SQL/ORM logic.
"""

import json
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from app.db.models import InspectionRecord


def create_inspection_record(
    db: Session,
    status: str,
    confidence_score: float,
    extracted_texts: List[Any],
    violations: List[Any],
    image_path: Optional[str] = None
) -> InspectionRecord:
    """
    Persists a new commodity package inspection record to the database.
    """
    record = InspectionRecord(
        status=status,
        confidence_score=confidence_score,
        extracted_texts_json=json.dumps(extracted_texts),
        violations_json=json.dumps(violations),
        image_path=image_path,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_inspection_record(db: Session, record_id: int) -> Optional[InspectionRecord]:
    """
    Retrieves an inspection record by its primary key ID.
    """
    return db.query(InspectionRecord).filter(InspectionRecord.id == record_id).first()


def list_inspection_records(db: Session, skip: int = 0, limit: int = 100) -> List[InspectionRecord]:
    """
    Retrieves a paginated list of inspection records.
    """
    return db.query(InspectionRecord).order_by(InspectionRecord.id.desc()).offset(skip).limit(limit).all()
