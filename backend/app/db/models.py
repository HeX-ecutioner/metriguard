import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class InspectionStatus(str, enum.Enum):
    """Lifecycle status for a commodity inspection workflow."""
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FAILED = "FAILED"


class ViolationSeverity(str, enum.Enum):
    """Severity classification for regulatory rule violations."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Inspection(Base):
    """
    Represents an inspection session for a packaged commodity.
    Main root entity of the inspection workflow.
    """
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    status = Column(
        SQLEnum(InspectionStatus, native_enum=False, create_constraint=True),
        default=InspectionStatus.CREATED,
        nullable=False,
        index=True
    )
    product_name = Column(String(255), nullable=True)
    overall_confidence = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    images = relationship(
        "PackageImage",
        back_populates="inspection",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PackageImage.id"
    )
    declarations = relationship(
        "Declaration",
        back_populates="inspection",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Declaration.id"
    )
    violations = relationship(
        "Violation",
        back_populates="inspection",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Violation.id"
    )
    result = relationship(
        "InspectionResult",
        back_populates="inspection",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class PackageImage(Base):
    """
    Represents an uploaded image of the packaged commodity label/packaging.
    """
    __tablename__ = "package_images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(
        Integer,
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="images")


class Declaration(Base):
    """
    Represents a specific mandatory or voluntary declaration extracted from the package
    (e.g., MRP, Net Quantity, Manufacturer, Date of Packing).
    """
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(
        Integer,
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    declaration_type = Column(String(100), nullable=False, index=True)
    extracted_value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    source_image_id = Column(
        Integer,
        ForeignKey("package_images.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    bounding_box = Column(Text, nullable=True)  # JSON-serialized coordinates
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="declarations")
    source_image = relationship("PackageImage", foreign_keys=[source_image_id])


class Violation(Base):
    """
    Represents a specific compliance violation detected against a Legal Metrology rule.
    Every violation is traceable to a rule and supports visual/textual evidence.
    """
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(
        Integer,
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rule_id = Column(String(100), nullable=False, index=True)
    rule_version = Column(String(50), nullable=False, default="2011")
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    severity = Column(
        SQLEnum(ViolationSeverity, native_enum=False, create_constraint=True),
        nullable=False,
        default=ViolationSeverity.ERROR,
        index=True
    )
    confidence = Column(Float, nullable=True)
    evidence_image_id = Column(
        Integer,
        ForeignKey("package_images.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    evidence_bounding_box = Column(Text, nullable=True)  # JSON coordinates
    measured_value = Column(String(255), nullable=True)
    expected_value = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="violations")
    evidence_image = relationship("PackageImage", foreign_keys=[evidence_image_id])


class InspectionResult(Base):
    """
    Represents the synthesized final outcome of an inspection.
    Maintains regulatory outcome separation from raw extractions.
    """
    __tablename__ = "inspection_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(
        Integer,
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    final_status = Column(
        SQLEnum(InspectionStatus, native_enum=False, create_constraint=True),
        nullable=False
    )
    summary = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="result")


# Backwards compatibility alias for existing skeleton references
InspectionRecord = Inspection
