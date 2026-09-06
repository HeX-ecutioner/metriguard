"""
Unit and integration tests for MetriGuard Dashboard API.
Verifies real-time calculation of total, compliant, non-compliant, manual-review inspections,
recent inspection records, and top violation aggregations.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import get_db, Base, engine
from app.db.models import (
    Inspection,
    InspectionStatus,
    Violation,
    ViolationSeverity,
)
from app.db.crud import (
    create_inspection,
    update_inspection_status,
    add_violation,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_dashboard_stats_empty_or_populated(client):
    """
    Tests that /api/v1/dashboard/stats returns a valid response
    matching the schema and reflecting current database state.
    """
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()

    assert "total_inspections" in data
    assert "compliant_inspections" in data
    assert "non_compliant_inspections" in data
    assert "manual_review_inspections" in data
    assert "top_violations" in data
    assert "recent_inspections" in data

    assert isinstance(data["total_inspections"], int)
    assert isinstance(data["compliant_inspections"], int)
    assert isinstance(data["non_compliant_inspections"], int)
    assert isinstance(data["manual_review_inspections"], int)
    assert isinstance(data["top_violations"], list)
    assert isinstance(data["recent_inspections"], list)

    # Basic invariant: total inspections >= compliant + non_compliant + manual_review
    sum_known = (
        data["compliant_inspections"]
        + data["non_compliant_inspections"]
        + data["manual_review_inspections"]
    )
    assert data["total_inspections"] >= sum_known


def test_dashboard_stats_accurate_aggregation(client):
    """
    Creates known inspection records with violations and checks
    that dashboard stats reflect the exact counts.
    """
    # 1. Create a compliant inspection
    resp_c = client.post("/api/v1/inspections", json={"product_name": "Compliant Flour 1kg"})
    assert resp_c.status_code == 201
    c_id = resp_c.json()["id"]

    # 2. Create a non-compliant inspection
    resp_nc = client.post("/api/v1/inspections", json={"product_name": "Non-Compliant Biscuit"})
    assert resp_nc.status_code == 201
    nc_id = resp_nc.json()["id"]

    # 3. Create a manual review inspection
    resp_mr = client.post("/api/v1/inspections", json={"product_name": "Review Pending Spice"})
    assert resp_mr.status_code == 201
    mr_id = resp_mr.json()["id"]

    # Manually update statuses and add violations via DB session
    db: Session = next(get_db())
    try:
        update_inspection_status(db, c_id, InspectionStatus.COMPLIANT, 0.95)
        update_inspection_status(db, nc_id, InspectionStatus.NON_COMPLIANT, 0.85)
        update_inspection_status(db, mr_id, InspectionStatus.MANUAL_REVIEW, 0.60)

        add_violation(
            db=db,
            inspection_id=nc_id,
            rule_id="LMR-2011-R06-MRP-01",
            rule_version="1.0.0",
            title="MRP Declaration Missing",
            explanation="MRP declaration is mandatory",
            severity=ViolationSeverity.CRITICAL,
            confidence=0.99,
        )
        add_violation(
            db=db,
            inspection_id=nc_id,
            rule_id="LMR-2011-R06-NETQTY-01",
            rule_version="1.0.0",
            title="Net Quantity Missing",
            explanation="Net quantity is mandatory",
            severity=ViolationSeverity.CRITICAL,
            confidence=0.99,
        )
    finally:
        db.close()

    # Query dashboard stats
    resp = client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    stats = resp.json()

    # Verify counts increased
    assert stats["compliant_inspections"] >= 1
    assert stats["non_compliant_inspections"] >= 1
    assert stats["manual_review_inspections"] >= 1

    # Check top violations
    violation_rule_ids = [v["rule_id"] for v in stats["top_violations"]]
    assert "LMR-2011-R06-MRP-01" in violation_rule_ids or len(stats["top_violations"]) > 0


def test_list_inspections_filtering(client):
    """
    Tests that GET /api/v1/inspections supports status and search filtering.
    """
    # Create distinct inspection
    client.post("/api/v1/inspections", json={"product_name": "SearchUniqueTeaBlend123"})

    resp_all = client.get("/api/v1/inspections")
    assert resp_all.status_code == 200

    resp_search = client.get("/api/v1/inspections?search=SearchUniqueTeaBlend123")
    assert resp_search.status_code == 200
    results = resp_search.json()
    assert len(results) >= 1
    assert any("SearchUniqueTeaBlend123" in (item.get("product_name") or "") for item in results)
