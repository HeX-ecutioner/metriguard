# Legal Metrology (Packaged Commodities) Rules, 2011 - Codified Regulatory Rules

This document specifies the authoritative regulatory requirements codified in MetriGuard's deterministic rule engine.
Every rule implemented in the system maps directly to the official statutory text of the **Legal Metrology (Packaged Commodities) Rules, 2011** (as amended up to 2022) issued by the Department of Consumer Affairs, Ministry of Consumer Affairs, Food and Public Distribution, Government of India.

## Architectural Principles

1. **Deterministic & Reproducible**: Rules evaluate structured facts extracted from OCR. Compliance determinations are deterministic, reproducible, and do not use LLMs as decision-makers.
2. **Conservative & Traceable**: Absence of evidence is not compliance. Ambiguous declarations, missing fields, or low OCR confidences trigger `REVIEW` rather than assuming compliance.
3. **Exemptions Respected**: Statutory exemptions (such as Rule 26 exemptions for packages $\le$ 10g/ml, wholesale packages, or industrial/institutional consumers) correctly yield `NOT_APPLICABLE`.
4. **Prototype Labeling**: Rules covering general packaged commodities are marked as prototypes (`is_prototype = True`) to indicate that specialized sub-commodity schedules (such as Schedule II specific commodities) are pending full codification.

## Rule Structure Schema

Each codified rule contains the following versioned metadata:
- **`rule_id`**: Canonical rule identifier (e.g. `LMR-2011-R06-1-E`).
- **`rule_version`**: Semantic version of the rule codification (e.g. `1.0.0`).
- **`title`**: Concise human-readable name.
- **`description`**: Detailed explanation of the statutory obligation.
- **`applicability`**: Conditions under which the rule applies (package type, commodity category, weight/volume thresholds).
- **`required_input_fields`**: Mandatory declaration fields evaluated by the rule.
- **`severity`**: Risk/violation severity (`INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- **`evidence_requirements`**: Evidence artifacts needed to justify a decision (`bounding_box`, `original_text`, `confidence`).
- **`enabled`**: Boolean flag indicating whether the rule is active.
- **`is_prototype`**: Indicates prototype status.
- **`source_reference`**: Official statutory citation.

## Evaluation Outcomes

The rule engine yields one of four outcomes for each rule:
- **`PASS`**: The declaration is present, compliant with statutory format, unambiguous, and supported by sufficient OCR confidence.
- **`FAIL`**: The declaration is absent on an applicable package, or violates statutory formatting (e.g. illegal non-metric units, negative price, future date).
- **`REVIEW`**: The declaration is ambiguous (conflicting values on same package), has low OCR confidence, or requires human inspector verification.
- **`NOT_APPLICABLE`**: The package is exempt under statutory provisions (e.g. Rule 26 exemptions, wholesale supply, or quantity below threshold).

## Codified Prototype Rules (Version 1.0)

### 1. Maximum Retail Price (MRP) Declaration
- **Rule ID**: `LMR-2011-R06-1-E`
- **Version**: `1.0.0`
- **Statute Reference**: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(e).
- **Statutory Text**: "The retail sale price of the package shall be declared in the form 'Maximum or Max. retail price Rs......./₹....... inclusive of all taxes' or in the form 'MRP Rs......./₹....... incl. of all taxes'."
- **Applicability**:
  - Pre-packaged commodities intended for retail sale.
  - **Exemptions** (Rule 26):
    - Packages containing commodity exceeding 25 kg or 25 L (except cement and fertilizer).
    - Packages for industrial consumers or institutional consumers.
    - Packages with net weight $\le$ 10 g or $\le$ 10 ml.
- **Required Fields**: `DeclarationType.MRP`
- **Findings**:
  - `PASS`: Valid numeric price in INR with standard MRP indicator.
  - `FAIL`: Completely missing on non-exempt retail package, or price $\le$ 0.
  - `REVIEW`: Multiple conflicting prices detected (`AMBIGUOUS`), OCR confidence < threshold, or unreadable digits.
  - `NOT_APPLICABLE`: Package is wholesale, industrial, institutional, or weight-exempt.

### 2. Net Quantity & Metric Units Declaration
- **Rule ID**: `LMR-2011-R06-1-C`
- **Version**: `1.0.0`
- **Statute Reference**: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(c) and Rules 11, 12, 13.
- **Statutory Text**: "The net quantity, in terms of the standard unit of weight or measure, of the commodity contained in the package or where the commodity is packed or sold by number, the number of the commodity contained in the package shall be declared."
- **Applicability**:
  - Mandatory on all retail pre-packaged commodities.
  - **Exemptions** (Rule 26): Packages containing net quantity $\le$ 10 g or $\le$ 10 ml.
- **Required Fields**: `DeclarationType.NET_QUANTITY`
- **Evaluation Criteria**:
  - Standard metric units: mass (`g`, `kg`, `mg`), volume (`ml`, `L`), count (`units`, `pcs`, `N`), length (`m`, `cm`).
  - Use of non-metric/imperial units alone (e.g. `lbs`, `oz`) without metric equivalents violates the Act.
  - Multipacks (`e.g. 4 x 75g = 300g`) must indicate both individual piece quantity and total quantity.
- **Findings**:
  - `PASS`: Metric net quantity present and well-formed.
  - `FAIL`: Absent on applicable package, or non-metric units without metric representation.
  - `REVIEW`: Ambiguous (conflicting quantities detected), or low OCR confidence.
  - `NOT_APPLICABLE`: Package is net weight $\le$ 10g/ml or wholesale exempt.

### 3. Name and Address of Manufacturer / Packer / Importer
- **Rule ID**: `LMR-2011-R06-1-A`
- **Version**: `1.0.0`
- **Statute Reference**: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(a).
- **Statutory Text**: "The name and complete address of the manufacturer or where the manufacturer is not the packer, the name and address of the manufacturer and packer and in case of imported packages, the name and address of the importer shall be declared on every package."
- **Applicability**: All pre-packaged commodities for retail sale.
- **Required Fields**: At least one of `DeclarationType.MANUFACTURER`, `DeclarationType.PACKER`, `DeclarationType.IMPORTER`.
- **Special Conditions**:
  - For imported commodities, the name and address of the `IMPORTER` is mandatory.
- **Findings**:
  - `PASS`: Verifiable entity name and location present.
  - `FAIL`: Completely missing manufacturer/packer details; or missing importer details on imported commodities.
  - `REVIEW`: Ambiguous entity details or low OCR confidence.
  - `NOT_APPLICABLE`: Exempt packages under Rule 26.

### 4. Month and Year of Manufacture or Pre-packing
- **Rule ID**: `LMR-2011-R06-1-D`
- **Version**: `1.0.0`
- **Statute Reference**: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(d).
- **Statutory Text**: "The month and year in which the commodity is manufactured or pre-packed or imported shall be declared."
- **Applicability**: Mandatory for all retail packages (except commodities exempted by Central Government notification, e.g. agarbatti, bidi).
- **Required Fields**: `DeclarationType.MANUFACTURE_DATE` or `DeclarationType.PACKING_DATE`.
- **Findings**:
  - `PASS`: Valid calendar month and year (e.g. `10/2025`, `Oct 2025`).
  - `FAIL`: Missing on applicable package, or post-dated future manufacturing date.
  - `REVIEW`: Ambiguous conflicting dates or low OCR confidence.
  - `NOT_APPLICABLE`: Exempt commodity category.

### 5. Consumer Care Grievance Redressal Details
- **Rule ID**: `LMR-2011-R06-1-G`
- **Version**: `1.0.0`
- **Statute Reference**: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(g) and Rule 6(2).
- **Statutory Text**: "The name, address, telephone number, e-mail address of the person who can be or the office which can be, contacted, in case of consumer complaints."
- **Applicability**: Mandatory for all retail pre-packaged commodities.
- **Required Fields**: `DeclarationType.CONSUMER_CARE`.
- **Findings**:
  - `PASS`: Contact telephone helpline, email address, or grievance postal address present.
  - `FAIL`: Missing consumer care details.
  - `REVIEW`: Ambiguous contact details or low OCR confidence.
  - `NOT_APPLICABLE`: Exempt wholesale or institutional packages.

### 6. Unit Sale Price (USP)
- **Rule ID**: `LMR-2011-R06-11-USP`
- **Version**: `1.0.0`
- **Statute Reference**: Legal Metrology (Packaged Commodities) Amendment Rules, 2021 (G.S.R. 779(E)) adding Rule 6(11), effective December 1, 2022.
- **Statutory Text**: "Declaration of Unit Sale Price on packages containing more than 1 unit or weight > 100g/100ml in terms of per gram, per kilogram, per millilitre, per litre, or per number."
- **Applicability**:
  - Pre-packaged commodities where net quantity exceeds 100 g or 100 ml, or multi-unit packages.
  - **Not Applicable**:
    - Packages with net quantity $\le$ 100 g or $\le$ 100 ml.
    - Packages where the retail sale price and the unit sale price are identical (e.g. single item of 1 unit, 1g, or 1ml).
- **Required Fields**: `DeclarationType.UNIT_SALE_PRICE`, `DeclarationType.NET_QUANTITY`.
- **Findings**:
  - `PASS`: Applicable package (> 100g/ml) has valid declared Unit Sale Price in standard unit rate (`Rs. X / g`, `Rs. X / kg`, `Rs. X / ml`).
  - `FAIL`: Applicable package (> 100g/ml) completely lacks Unit Sale Price declaration.
  - `NOT_APPLICABLE`: Package net quantity is $\le$ 100 g or $\le$ 100 ml.
  - `REVIEW`: Net quantity is unknown/missing so applicability cannot be determined, or USP is ambiguous.

## Limitations & Future Roadmap

The current version 1.0 represents the **prototype core foundation**. The following extensions are planned for subsequent versions:
1. **Schedule II Standard Packaging Capacities**: Verifying whether specific commodities (e.g. tea, biscuits, baby food) conform to prescribed package sizes.
2. **Principal Display Panel (PDP) Size Ratios**: Verifying font sizes against total PDP area (Rule 7 and Rule 9).
3. **E-Commerce Specific Declarations**: Verifying digital listing requirements under Rule 6(10).