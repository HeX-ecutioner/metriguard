"""
Dashboard API router for MetriGuard.
Serves real aggregated metrics, statistics, and recent inspection data directly from SQLite.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.crud import get_dashboard_stats
from app.models.schemas import InspectionDetailResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class TopViolationStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rule_id: str
    title: str
    severity: str
    count: int


class DashboardStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_inspections: int
    compliant_inspections: int
    non_compliant_inspections: int
    manual_review_inspections: int
    top_violations: List[TopViolationStat] = []
    recent_inspections: List[InspectionDetailResponse] = []


@router.get("/stats", response_model=DashboardStatsResponse, summary="Retrieve aggregated dashboard metrics")
def get_dashboard_statistics(db: Session = Depends(get_db)):
    """
    Returns real-time dashboard analytics derived directly from the SQLite database:
    - Total inspection counts and compliance status breakdown
    - Top violation types aggregated by rule ID and title
    - Recent inspection session summaries
    """
    stats = get_dashboard_stats(db=db)
    return stats
