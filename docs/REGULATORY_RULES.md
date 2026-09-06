# MetriGuard Regulatory Compliance Rules Specification

## 1. Purpose and Scope
This document specifies the codified regulatory compliance rules implemented in **MetriGuard** for evaluating pre-packaged commodities under the **Legal Metrology (Packaged Commodities) Rules, 2011** (problem statement **SIH26034**).

The scope is strictly limited to the 6 codified prototype rules implemented in [`backend/app/services/rules/lmr_2011/`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011).

## 2. Regulatory Disclaimer
> [!IMPORTANT]
> **MetriGuard is an AI-assisted packaged-commodity inspection prototype.**
> - It is designed for demonstration, research, and testing purposes.
> - **It is not a legally certified compliance authority or court-admissible enforcement system.**
> - OCR text extractions and rule evaluation outcomes must be independently reviewed and verified by qualified human legal metrology inspectors before any regulatory action or notice is issued.

## 3. Rule-Engine Principles
1. **100% Deterministic Evaluation:** Compliance rules operate on structured extracted facts, completely isolated from AI/LLM non-deterministic generation.
2. **Strict Evidence Linking:** Every rule outcome must link directly to verifiable OCR text snippets and bounding box coordinates `[x_min, y_min, x_max, y_max]`.
3. **Safe Manual Review Routing:** Any missing mandatory field, ambiguous multi-candidate value, or low-confidence extraction (< `0.60` / `0.70`) automatically routes to `MANUAL_REVIEW`.
4. **Version Control:** All rules maintain explicit semantic version strings (`1.0.0`) to ensure auditability and regression tracking.

## 4. Rule-Set Versioning Policy
- Rule sets are grouped by regulatory act and year (e.g., `LMR_2011`).
- Individual rules maintain a `rule_version` property (e.g., `1.0.0`).
- Breaking changes to rule validation logic or required input schemas require incrementing the major version.

## 5. Implemented Rule Inventory

| Rule ID | Rule Name | Version | Regulatory Reference | Source File |
| :--- | :--- | :--- | :--- | :--- |
| `LMR-2011-R06-1-E` | Maximum Retail Price (MRP) Declaration | 1.0.0 | Rule 6(1)(e) | [`r06_1_e_mrp.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_e_mrp.py) |
| `LMR-2011-R06-1-C` | Net Quantity Declaration | 1.0.0 | Rule 6(1)(c) | [`r06_1_c_net_qty.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_c_net_qty.py) |
| `LMR-2011-R06-1-A` | Manufacturer / Packer / Importer Name & Address | 1.0.0 | Rule 6(1)(a) | [`r06_1_a_entity.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_a_entity.py) |
| `LMR-2011-R06-1-D` | Month and Year of Manufacture / Packing / Import | 1.0.0 | Rule 6(1)(d) | [`r06_1_d_date.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_d_date.py) |
| `LMR-2011-R06-1-G` | Consumer Care Details | 1.0.0 | Rule 6(1)(g) | [`r06_1_g_consumer.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_g_consumer.py) |
| `LMR-2011-R06-11` | Unit Sale Price (USP) Declaration | 1.0.0 | Rule 6(11) | [`r06_11_usp.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_11_usp.py) |

## 6. Detailed Specifications of Implemented Rules

### 6.1 `LMR-2011-R06-1-E`: Maximum Retail Price (MRP) Declaration
- **Rule ID:** `LMR-2011-R06-1-E`
- **Rule Name:** Maximum Retail Price (MRP) Declaration
- **Rule Version:** `1.0.0`
- **Applicable Condition:** All retail pre-packaged commodities (Exempt if net weight $\le$ 10g or net volume $\le$ 10ml under Rule 26(a)).
- **Required Declaration:** `DeclarationType.MRP`
- **Input Fields:** `mrp` declaration value, confidence, extraction status, net weight/volume facts.
- **Validation Logic:**
  1. Checks Rule 26(a) weight/volume exemption.
  2. Verifies presence of MRP declaration string.
  3. Checks for ambiguous multi-price candidates.
  4. Validates numerical monetary value > 0 in Indian Rupees (`Rs.` / `₹`).
- **Evidence Requirement:** Bounding box coordinates and OCR text snippet of MRP declaration.
- **Confidence Requirement:** $\ge 0.60$; lower confidence routes to `MANUAL_REVIEW`.
- **Failure Behavior:** Returns `FAILED` finding if MRP is missing, zero/negative, or malformed without valid numerical amount.
- **Relevant Source File:** [`backend/app/services/rules/lmr_2011/r06_1_e_mrp.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_e_mrp.py)
- **Relevant Test File:** [`backend/tests/test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py)

### 6.2 `LMR-2011-R06-1-C`: Net Quantity Declaration
- **Rule ID:** `LMR-2011-R06-1-C`
- **Rule Name:** Net Quantity Declaration
- **Rule Version:** `1.0.0`
- **Applicable Condition:** All retail pre-packaged commodities.
- **Required Declaration:** `DeclarationType.NET_QUANTITY`
- **Input Fields:** `net_quantity` declaration value, confidence, extraction status.
- **Validation Logic:**
  1. Verifies presence of net quantity declaration string.
  2. Validates numerical amount and standard legal measurement unit (`g`, `kg`, `ml`, `l`, `m`, `cm`, `N`, `PCS`).
  3. Rejects non-standard or informal units.
- **Evidence Requirement:** Bounding box coordinates and OCR text snippet for Net Quantity.
- **Confidence Requirement:** $\ge 0.60$; lower confidence routes to `MANUAL_REVIEW`.
- **Failure Behavior:** Returns `FAILED` finding if Net Quantity is missing or lacks standard units.
- **Relevant Source File:** [`backend/app/services/rules/lmr_2011/r06_1_c_net_qty.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_c_net_qty.py)
- **Relevant Test File:** [`backend/tests/test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py)

### 6.3 `LMR-2011-R06-1-A`: Manufacturer / Packer / Importer Name & Address
- **Rule ID:** `LMR-2011-R06-1-A`
- **Rule Name:** Manufacturer / Packer / Importer Entity Name and Address
- **Rule Version:** `1.0.0`
- **Applicable Condition:** All retail pre-packaged commodities.
- **Required Declaration:** `DeclarationType.MANUFACTURER`, `DeclarationType.PACKER`, or `DeclarationType.IMPORTER`
- **Input Fields:** Entity name & address string, confidence, extraction status.
- **Validation Logic:**
  1. Checks for at least one valid entity declaration (Manufacturer, Packer, or Importer).
  2. Validates that declared string contains both name and address components (pin code, city, or state indicators).
- **Evidence Requirement:** Bounding box coordinates and text snippet for entity declaration.
- **Confidence Requirement:** $\ge 0.60$; lower confidence routes to `MANUAL_REVIEW`.
- **Failure Behavior:** Returns `FAILED` finding if no entity name/address is declared.
- **Relevant Source File:** [`backend/app/services/rules/lmr_2011/r06_1_a_entity.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_a_entity.py)
- **Relevant Test File:** [`backend/tests/test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py)

### 6.4 `LMR-2011-R06-1-D`: Month and Year of Manufacture / Packing / Import
- **Rule ID:** `LMR-2011-R06-1-D`
- **Rule Name:** Month and Year of Manufacture / Packing / Import
- **Rule Version:** `1.0.0`
- **Applicable Condition:** All retail pre-packaged commodities.
- **Required Declaration:** `DeclarationType.MANUFACTURE_DATE`, `PACKING_DATE`, or `IMPORT_DATE`
- **Input Fields:** Date declaration string, confidence, extraction status.
- **Validation Logic:**
  1. Verifies presence of valid month and year declaration (e.g. `MM/YYYY`, `MMM YYYY`, `MM/YY`).
  2. Validates month range (`01`-`12`) and year boundaries.
- **Evidence Requirement:** Bounding box coordinates and text snippet for date declaration.
- **Confidence Requirement:** $\ge 0.60$; lower confidence routes to `MANUAL_REVIEW`.
- **Failure Behavior:** Returns `FAILED` finding if manufacture/packing date is missing or invalid.
- **Relevant Source File:** [`backend/app/services/rules/lmr_2011/r06_1_d_date.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_d_date.py)
- **Relevant Test File:** [`backend/tests/test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py)

### 6.5 `LMR-2011-R06-1-G`: Consumer Care Details
- **Rule ID:** `LMR-2011-R06-1-G`
- **Rule Name:** Consumer Care Contact Details
- **Rule Version:** `1.0.0`
- **Applicable Condition:** All retail pre-packaged commodities.
- **Required Declaration:** `DeclarationType.CONSUMER_CARE`
- **Input Fields:** Consumer care declaration string, phone, email, address fields.
- **Validation Logic:**
  1. Verifies presence of consumer care contact info.
  2. Checks for at least one valid contact channel (Telephone number, Email address, or Postal address).
- **Evidence Requirement:** Bounding box coordinates and text snippet for consumer care section.
- **Confidence Requirement:** $\ge 0.60$; lower confidence routes to `MANUAL_REVIEW`.
- **Failure Behavior:** Returns `FAILED` finding if consumer care details are completely absent.
- **Relevant Source File:** [`backend/app/services/rules/lmr_2011/r06_1_g_consumer.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_1_g_consumer.py)
- **Relevant Test File:** [`backend/tests/test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py)

### 6.6 `LMR-2011-R06-11`: Unit Sale Price (USP) Declaration
- **Rule ID:** `LMR-2011-R06-11`
- **Rule Name:** Unit Sale Price (USP) Declaration
- **Rule Version:** `1.0.0`
- **Applicable Condition:** Pre-packaged commodities with net quantity > 100g or > 100ml.
- **Required Declaration:** `DeclarationType.UNIT_SALE_PRICE`
- **Input Fields:** `unit_sale_price` value, net weight/volume facts, confidence.
- **Validation Logic:**
  1. Checks if net quantity > 100g or > 100ml (packages $\le$ 100g/ml are exempt).
  2. Verifies declared unit rate format (e.g. `Rs. X / g`, `Rs. X / kg`, `Rs. X / ml`).
- **Evidence Requirement:** Bounding box coordinates and text snippet for USP declaration.
- **Confidence Requirement:** $\ge 0.60$; lower confidence routes to `MANUAL_REVIEW`.
- **Failure Behavior:** Returns `FAILED` finding if USP is required but missing.
- **Relevant Source File:** [`backend/app/services/rules/lmr_2011/r06_11_usp.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/r06_11_usp.py)
- **Relevant Test File:** [`backend/tests/test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py)

## 7. Manual-Review Conditions
An inspection evaluation automatically routes to `MANUAL_REVIEW` under any of the following conditions:
1. **Low Confidence:** Extracted declaration confidence score is below `0.60` (rule-level) or overall confidence is below `0.70`.
2. **Missing Mandatory Declaration:** Any required declaration (e.g. Net Qty or MRP) is missing or unreadable on the image label.
3. **Ambiguous Multi-Candidate Extractions:** Multiple conflicting prices or dates are detected on the same image.
4. **OCR Failure or Exception:** Any OCR execution error or internal processing exception during image parsing.

## 8. Unsupported or Unimplemented Rules
The following regulatory rules are **not** currently implemented in the rule engine:
- **Schedule II Standard Capacities:** Prescribed package sizes for specific commodities (biscuits, tea, baby food).
- **Principal Display Panel (PDP) Size Ratios:** Font size calculations relative to package surface area (Rule 7 / Rule 9).
- **E-Commerce Specific Digital Listing Rules:** Digital marketplace display requirements under Rule 6(10).

## 9. Rule-Change Procedure
1. Create a new Python module in `backend/app/services/rules/lmr_2011/` inheriting from `RegulatoryRule`.
2. Assign a unique `rule_id`, semantic `rule_version`, `title`, `description`, and `required_input_fields`.
3. Implement `evaluate(self, facts: PackageFacts) -> RuleFinding`.
4. Register the rule instance in `get_lmr_2011_prototype_rules()` in [`backend/app/services/rules/lmr_2011/__init__.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/rules/lmr_2011/__init__.py).

## 10. Testing & Approval Requirements for Rule Changes
- **Unit Tests:** Add comprehensive unit test cases in [`backend/tests/test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py) covering pass, fail, exemption, low confidence, and ambiguous scenarios.
- **Regression Verification:** Run `pytest backend/tests` to verify zero regression across existing rule evaluations.

## 11. Known Regulatory Limitations
- **Single-Face Label Scanning:** Declarations split across separate front and back package faces cannot be unified in a single inspection session without scanning both faces in separate sessions.
- **Illustrative Rule Thresholds:** Confidence threshold values (`0.60`, `0.70`) and regex patterns are engineered for typical retail labels and may require tuning for non-standard typography.