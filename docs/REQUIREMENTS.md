# MetriGuard Software Requirements Specification (SRS)

## 1. Document Purpose
This document defines the formal functional, non-functional, security, and quality requirements for **MetriGuard**, an AI-assisted packaged-commodity inspection system prototype. It serves as the single source of truth for system capabilities, verification criteria, and project boundaries for problem statement **SIH26034**.

## 2. Project Scope
MetriGuard provides automated assistance to inspectors by scanning pre-packaged commodity labels, extracting mandatory regulatory declarations, and evaluating compliance against specified rules under the Indian Legal Metrology (Packaged Commodities) Rules, 2011.

- **In Scope:** Single-image package processing, label image validation, OCR text extraction, regex declaration parsing, deterministic rule evaluation (6 LMR 2011 rules), evidence logging, manual review UI, history tracking, and metric dashboard.
- **Out of Scope:** Legal certification, court-admissible automated enforcement, multi-image inspection sessions, automated LLM legal decision-making, and full legal metrology coverage.

## 3. Intended Users
- **Package Inspector / Verification Operator:** Primary user who uploads package images, reviews extracted declarations, inspects evidence bounding boxes, and performs manual review overrides.
- **System Administrator / Developer:** Evaluates inspection accuracy, maintains rule definitions, and monitors system performance metrics.

## 4. Problem Statement
Manual inspection of packaged commodities under SIH26034 is time-consuming, prone to human error, and lacks automated evidence tracking. MetriGuard addresses this by combining computer vision and deterministic legal rules to highlight compliance violations while keeping human inspectors in the loop.

## 5. System Objectives
1. **Explainable AI & Evidence:** Every compliance determination must link to exact OCR text evidence and bounding box coordinates.
2. **Determinism & Accuracy:** Legal compliance rules must be versioned and 100% deterministic, preventing non-deterministic AI hallucinations.
3. **Safe Manual Review:** Low-confidence extractions or ambiguous declarations must automatically trigger a `MANUAL_REVIEW` workflow.
4. **Single-Image Session Integrity:** Ensure an inspection session strictly processes exactly one package image.

## 6. Detailed Requirements Matrix

| Req ID | Requirement Description | Category | Priority | Status | Verification Method |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FR-001** | The system shall accept single package image uploads in JPEG, PNG, or WEBP formats up to 10 MB in size. | Functional | HIGH | Implemented | Automated Test / Inspection |
| **FR-002** | The system shall validate uploaded image structural byte integrity and MIME type before processing. | Functional | HIGH | Implemented | Automated Test |
| **FR-003** | The system shall generate a secure UUID file key and store images in local disk storage (`data/uploads/`). | Functional | HIGH | Implemented | Code Inspection / Test |
| **FR-004** | The system shall extract raw text, bounding box coordinates `[x_min, y_min, x_max, y_max]`, and confidence scores via OCR. | Functional | HIGH | Implemented | Automated Test |
| **FR-005** | The system shall parse mandatory declarations (MRP, Net Qty, Mfg Date, Expiry Date, Entity details, Consumer Care, USP) using regular expressions. | Functional | HIGH | Implemented | Automated Test |
| **FR-006** | The system shall evaluate compliance using 6 versioned LMR 2011 deterministic rules (`r06_1_a_entity`, `r06_1_c_net_qty`, `r06_1_d_date`, `r06_1_e_mrp`, `r06_1_g_consumer`, `r06_11_usp`). | Functional | HIGH | Implemented | Automated Test |
| **FR-007** | The system shall assign a final inspection outcome status (`COMPLIANT`, `NON_COMPLIANT`, `MANUAL_REVIEW`, or `FAILED`). | Functional | HIGH | Implemented | Demonstration / Test |
| **FR-008** | The system shall provide a manual review interface allowing operators to view bounding boxes and override inspection status (`PATCH /api/v1/inspections/{id}/status`). | Functional | HIGH | Implemented | Manual UI Test |
| **FR-009** | The system shall maintain inspection history and dashboard summary statistics (`GET /api/v1/dashboard/metrics`). | Functional | MEDIUM | Implemented | Manual UI Test |
| **FR-010** | The system shall support deleting an inspection record and purging its stored image file (`DELETE /api/v1/inspections/{id}`). | Functional | MEDIUM | Implemented | Automated Test |
| **FR-011** | The system shall support optional LLM-assisted extraction (`AIExtractor`) when regex extraction confidence falls below threshold. | Functional | LOW | Partially Implemented | Code Analysis |
| **FR-012** | The system shall support multi-role user authentication (RBAC) and user session management. | Functional | MEDIUM | Not Implemented | Inspection |
| **NFR-001** | **Single Image Contract:** One inspection session shall contain strictly one package image, one OCR result, one declaration extraction set, and one compliance result. | Non-Functional | HIGH | Implemented | Database Constraint / Test |
| **NFR-002** | Compliance evaluations shall be 100% deterministic and reproducible given identical extracted declarations. | Non-Functional | HIGH | Implemented | Automated Test |
| **NFR-003** | Standard image inspection execution shall complete within 5 seconds under standard CPU/GPU operations. | Non-Functional | MEDIUM | Implemented | Performance Demonstration |
| **SEC-001** | The system shall sanitize uploaded image filenames with UUID prefixes and verify paths using `is_relative_to` to prevent directory traversal. | Security | HIGH | Implemented | Automated Test / Code Review |
| **SEC-002** | System configuration and API credentials shall be loaded dynamically from local `.env` files via `pydantic-settings`. | Security | HIGH | Implemented | Code Inspection |
| **SEC-003** | API cross-origin requests shall be restricted using FastAPI `CORSMiddleware` based on `CORS_ORIGINS`. | Security | HIGH | Implemented | Code Inspection |
| **QA-001** | Backend and frontend codebases shall maintain passing automated unit/integration test suites (Pytest & Vitest). | Quality | HIGH | Implemented | Automated Test Executions |

## 7. Inspection Lifecycle Requirements
- **Lifecycle Flow:** `Upload` -> `Validate` -> `Store` -> `OCR Extract` -> `Declaration Parse` -> `Rule Evaluate` -> `Persist` -> `View/Review`.
- **Session Boundary:** Multi-image uploads within a single inspection session are prohibited. Subsequent image uploads create independent inspection sessions.

## 8. Image-Upload Requirements
- Maximum file size: 10 MB.
- Supported file extensions: `.jpg`, `.jpeg`, `.png`, `.webp`.
- Server-side byte validation: `PIL.Image.open().verify()` must pass; corrupt or fake images must be rejected with HTTP 400 Bad Request.

## 9. OCR and Declaration Extraction Requirements
- Raw OCR results must include text block strings, detection confidence `[0.0, 1.0]`, and bounding box coordinates normalized to original image dimensions.
- Parsed fields must include field-level confidence scores.
- Unidentified or missing fields must be set to `None` rather than fabricated values.

## 10. Rule Engine Requirements
- Rule evaluation must operate on structured extracted declarations, completely independent of raw OCR models.
- Rules must produce explicit status (`PASSED`, `FAILED`, `MANUAL_REVIEW`, `SKIPPED`), evidence text, and severity metrics (`CRITICAL`, `MAJOR`, `MINOR`, `WARNING`).

## 11. Evidence Requirements
- Inspection records must persist exact evidence text and bounding boxes for every rule evaluation.
- The UI must visually highlight bounding boxes on the package image when an inspector selects an extracted declaration or rule finding.

## 12. Confidence and Manual-Review Requirements
- Extraction confidence threshold default: `0.70`.
- If any mandatory declaration has extraction confidence < `0.70` or is missing, the system must set status to `MANUAL_REVIEW`.
- Manual review updates must be logged with timestamp and operator note.

## 13. Security and Privacy Requirements
- Uploaded package images must not be made publicly accessible without server running context.
- System must reject path manipulation characters (`../`, `\`, NULL bytes) in filenames.
- Users must be warned not to upload images containing personal identifiable information (PII).

## 14. Out-of-Scope Functionality
- Automated legal summons or penalty issuance.
- Cloud blob storage sync (S3/Azure Blob).
- Multi-tenant organization separation and SSO.
- Mobile native apps (iOS/Android).

## 15. Acceptance Criteria
- **AC-001 (Valid Image Inspection):** Uploading a valid commodity label image yields complete OCR text, parsed declarations, rule findings, and persistent database record within 5 seconds.
- **AC-002 (Invalid File Rejection):** Uploading an invalid file (e.g. `.exe` disguised as `.png` or file > 10MB) returns HTTP 400 with descriptive error message.
- **AC-003 (Deterministic Rules):** Running compliance checks on identical extracted declaration inputs yields identical rule pass/fail results across test runs.
- **AC-004 (Single Image Enforcement):** Database schema and API endpoints prevent linking multiple images to one inspection session.

## 16. Known Ambiguities & Open Questions
1. **Multi-Label Package Handling:** Packages with declarations split across front and back sides currently require separate single-image inspection sessions.
2. **Dynamic OCR Provider Selection:** PaddleOCR requires local binary dependencies; systems lacking PaddleOCR automatically fall back to mock OCR provider data.
