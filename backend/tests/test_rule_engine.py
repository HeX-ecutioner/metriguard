import pytest
from app.services.rule_engine import evaluate_compliance

def test_compliant_package():
    data = [
        {"text": "MRP Rs. 150", "confidence": 0.98},
        {"text": "Net Wt 500g", "confidence": 0.95},
        {"text": "Mfd. by MetriGuard Co.", "confidence": 0.99},
        {"text": "Mfg. Date 10/2025", "confidence": 0.92},
    ]
    result = evaluate_compliance(data)
    assert result.status == "COMPLIANT"
    assert len(result.violations) == 0
    assert result.confidence_score > 0.9

def test_non_compliant_package():
    data = [
        {"text": "MRP Rs. 150", "confidence": 0.98},
        {"text": "Net Wt 500g", "confidence": 0.95},
    ]
    result = evaluate_compliance(data)
    assert result.status == "NON_COMPLIANT"
    assert len(result.violations) == 2
    
def test_manual_review_package():
    data = [
        {"text": "MRP Rs. 150", "confidence": 0.50},
        {"text": "Net Wt 500g", "confidence": 0.50},
        {"text": "Mfd. by MetriGuard Co.", "confidence": 0.50},
        {"text": "Mfg. Date 10/2025", "confidence": 0.50},
    ]
    result = evaluate_compliance(data)
    assert result.status == "MANUAL_REVIEW"
