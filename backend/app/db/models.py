from app.db.database import Base, DB_AVAILABLE

if DB_AVAILABLE:
    from sqlalchemy import Column, Integer, String, Float, DateTime
    from sqlalchemy.sql import func

    class InspectionRecord(Base):
        __tablename__ = "inspections"

        id = Column(Integer, primary_key=True, index=True)
        status = Column(String, index=True)
        confidence_score = Column(Float)
        extracted_texts_json = Column(String)
        violations_json = Column(String)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
else:
    class InspectionRecord:
        pass

