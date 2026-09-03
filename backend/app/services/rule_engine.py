import re
from typing import List, Dict, Any
from app.models.schemas import InspectionResponse, RuleViolation

def evaluate_compliance(extracted_data: List[Dict[str, Any]]) -> InspectionResponse:
    """
    Deterministic Rule Engine based on Legal Metrology Rules, 2011 (Version 1.0)
    """
    violations = []
    extracted_texts = [item['text'] for item in extracted_data]
    
    full_text = " ".join(extracted_texts).lower()
    
    # Rule 1: MRP Declaration
    if not re.search(r'(mrp|max retail price|rs\.|₹)', full_text):
        violations.append(RuleViolation(
            rule_id="Rule 6(1)(e)",
            explanation="MRP (Retail Sale Price) declaration is missing.",
            confidence=1.0
        ))
        
    # Rule 2: Net Quantity
    if not re.search(r'(net weight|net wt|net vol|net qty|\d+\s*(g|kg|ml|l|gms|grams)\b)', full_text):
        violations.append(RuleViolation(
            rule_id="Rule 6(1)(c)",
            explanation="Net quantity declaration is missing.",
            confidence=1.0
        ))
        
    # Rule 3: Manufacturer / Packer Details
    if not re.search(r'(mfd\.?\s*by|packed\s*by|manufactured\s*by|imported\s*by)', full_text):
        violations.append(RuleViolation(
            rule_id="Rule 6(1)(a)",
            explanation="Manufacturer, packer, or importer details are missing.",
            confidence=1.0
        ))
        
    # Rule 4: Month and Year of Manufacture
    if not re.search(r'(mfd\. month|pkd\.|mfg\. date|mfg date|date of packing|pkd|\d{2}/\d{4})', full_text):
        violations.append(RuleViolation(
            rule_id="Rule 6(1)(d)",
            explanation="Month and year of manufacture or packing is missing.",
            confidence=1.0
        ))

    # Determine status based on violations and confidence
    status = "COMPLIANT"
    if len(violations) > 0:
        status = "NON_COMPLIANT"
    
    # Calculate an average confidence of the extracted data
    avg_confidence = sum([item['confidence'] for item in extracted_data]) / len(extracted_data) if extracted_data else 0.0
    
    if status == "COMPLIANT" and avg_confidence < 0.8:
        status = "MANUAL_REVIEW"
        
    return InspectionResponse(
        status=status,
        violations=violations,
        extracted_texts=extracted_texts,
        confidence_score=avg_confidence
    )
