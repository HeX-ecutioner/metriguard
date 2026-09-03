from typing import List, Optional
from pydantic import BaseModel

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
