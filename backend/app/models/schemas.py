from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Evidence(BaseModel):
    text: str
    box: Optional[BoundingBox] = None
    confidence: float


class RuleViolation(BaseModel):
    rule_id: str
    explanation: str
    evidence: Optional[Evidence] = None
    confidence: float


class InspectionResponse(BaseModel):
    status: str  # COMPLIANT, NON_COMPLIANT, MANUAL_REVIEW
    violations: List[RuleViolation]
    extracted_texts: List[str]
    confidence_score: float


# Schemas for Image Upload and Inspection Lifecycle Workflow
class InspectionCreateRequest(BaseModel):
    product_name: Optional[str] = None
    notes: Optional[str] = None


class PackageImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inspection_id: int
    file_path: str
    original_filename: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime
    status: Optional[str] = None
    confidence_score: Optional[float] = None
    extracted_texts: Optional[List[str]] = None
    violations: Optional[List[RuleViolation]] = None
    image_url: Optional[str] = None


class DeclarationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    declaration_type: str
    extracted_value: str
    confidence: Optional[float] = None
    source_image_id: Optional[int] = None
    bounding_box: Optional[str] = None


class ViolationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: str
    rule_version: str
    title: str
    explanation: str
    severity: str
    confidence: Optional[float] = None
    evidence_image_id: Optional[int] = None
    evidence_bounding_box: Optional[str] = None
    measured_value: Optional[str] = None
    expected_value: Optional[str] = None


class InspectionResultDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    final_status: str
    summary: str


class InspectionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    product_name: Optional[str] = None
    overall_confidence: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    images: List[PackageImageResponse] = []
    declarations: List[DeclarationDetailResponse] = []
    violations: List[ViolationDetailResponse] = []
    result: Optional[InspectionResultDetailResponse] = None


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
