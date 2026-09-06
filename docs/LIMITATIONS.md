# MetriGuard System Limitations & Risk Analysis

## 1. Purpose of This Document
This document provides an honest, transparent breakdown of the technical, optical, regulatory, and operational limitations of **MetriGuard**.

It explicitly outlines failure modes, edge cases, and architectural boundaries to ensure judges, inspectors, and maintainers understand what the prototype can and cannot guarantee for problem statement **SIH26034**.

## 2. Prototype Status & Non-Legal Authority Notice
> [!WARNING]
> **MetriGuard is an AI-assisted packaged-commodity inspection prototype.**
> - It is **not** a legally certified compliance authority or court-admissible enforcement tool.
> - Findings produced by the system (extractions, rule passes/fails, evidence text) do **not** constitute official legal notices.
> - All outputs must be independently reviewed and verified by a qualified Human Legal Metrology Inspector.

## 3. OCR & Optical Recognition Limitations
- **Character Confusion:** OCR engines (PaddleOCR / Tesseract) can occasionally confuse visually similar characters in packaging typography (e.g. `0` vs `O`, `1` vs `l`/`I`, `₹` vs `Rs.`, or decimal points `.`).
- **Stylized Typography & Branding Fonts:** Decorative or non-standard brand fonts on commercial packaging can degrade line detection and text extraction accuracy.
- **Language Scope:** The current regex pattern library ([`patterns.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/extraction/patterns.py)) and OCR engine focus primarily on English-language Legal Metrology declarations. Regional Indian language declarations are currently unsupported.

## 4. Image Quality, Lighting, & Environment Limitations
- **Image Resolution:** Low-resolution images (< 720p or width < 800px) degrade OCR text line segmentation and character recognition.
- **Blur & Motion Disruption:** Out-of-focus camera capture or motion blur prevents sharp character edge detection, safely routing the inspection to `MANUAL_REVIEW`.
- **Glare & Specular Reflection:** Metallic, glossy, or plastic foil packaging causes specular highlights that obscure mandatory declarations (e.g. MRP or batch numbers).

## 5. Geometric & Physical Packaging Limitations
- **Perspective Distortion & Extreme Angles:** Labels photographed at steep angles (> 30° tilt) distort bounding box geometry and character spacing.
- **Cylindrical & Curved Packaging:** Bottles, cans, or flexible pouches curve package text away from the camera, causing edge characters to compress or warp beyond OCR line grouping algorithms.
- **Tiny Typography:** Micro-printed batch codes or small font declarations (< 6pt physical height) may fail OCR segmentation unless captured in extreme macro close-ups.

## 6. Physical Measurement & Font-Size Calibration Limitations
- **Lack of Absolute Physical Scale:** A 2D photograph does not contain intrinsic physical scale information without a calibrated reference object (e.g. millimeter ruler or fiducial marker).
- **Principal Display Panel (PDP) Ratio Unverifiable:** Physical font height in millimeters (Rule 7 and Rule 9 requirements) cannot be measured accurately from uncalibrated 2D packaging photos alone.

## 7. Regulatory Scope Limitations
- **Implemented Rule Set Boundary:** The system checks **only** the 6 codified rules under the Legal Metrology (Packaged Commodities) Rules, 2011 (`LMR-2011-R06-1-A`, `R06-1-C`, `R06-1-D`, `R06-1-E`, `R06-1-G`, `R06-11`).
- **Unimplemented Regulatory Checks:** Schedule II standard packaging capacities, font height millimeter ratios, net weight tolerance variations, and e-commerce digital display rules are **not** evaluated.

## 8. Confidence, Evidence, & Manual Review Boundaries
- **No Evidence Invention:** The system will **never** fabricate or guess missing declaration values, bounding boxes, or rule evidence text.
- **Threshold Routing:** If extraction confidence falls below `0.60` (rule-level) or `0.70` (overall session-level), or if mandatory fields are missing/ambiguous, the inspection is routed to `MANUAL_REVIEW`.
- **Ambiguous Multi-Candidate Extractions:** Packages containing multiple price numbers or multiple dates trigger `MANUAL_REVIEW` to prevent automated misjudgment.

## 9. Performance & System Concurrency Limitations
- **Synchronous CPU Processing:** PaddleOCR runs synchronously in Uvicorn API worker threads ([`service.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/ocr/service.py)). High concurrent upload volumes without background queues (Celery/Redis) will cause request latency queuing.
- **Single-Node SQLite Database:** The database (`metriguard.db`) uses SQLite. While appropriate for single-station inspection prototypes, concurrent high-throughput write operations require migrating to PostgreSQL.

## 10. Data Storage & Security Limitations
- **Ephemeral Storage Risk:** Uploaded package images are saved to local server disk (`backend/data/uploads`). Deploying on stateless cloud containers (e.g. default Heroku/Render containers) without persistent volume attachments will result in image loss upon server restart.
- **Unauthenticated Prototype:** The API currently operates in open audit mode without user login, session tokens, or RBAC.

## 11. Known Unsupported Scenarios
1. **Multi-Face Packaging in One Session:** Scanning front and back packaging faces in a single combined inspection session is unsupported. Each face requires a separate single-image inspection session.
2. **Handwritten Declarations:** Handwritten packaging labels or stamped batch codes with low ink density are unsupported.
3. **Non-English Regional Text:** Package declarations printed exclusively in regional scripts (e.g. Hindi, Tamil, Bengali) without English declarations.

## 12. Required Human Verification Protocol
Every inspection output must be reviewed by a human inspector using the following verification protocol:
1. Compare the original packaging image against the extracted declaration values.
2. Verify bounding box overlays on the image viewer in `InspectionDetailView.tsx`.
3. Check flagged warnings in `MANUAL_REVIEW` cases.
4. Execute manual status override (`PATCH /api/v1/inspections/{id}/status`) before signing off on an inspection report.

## 13. Future Roadmap Improvements
1. **Multi-Image Package Session Support:** Allow linking multiple package faces (front, back, sides) into one unified inspection session.
2. **Regional Language OCR & Extraction:** Extend regex patterns and OCR dictionaries to support major regional Indian languages.
3. **Calibrated Physical Metric Measurement:** Support fiducial reference markers to enable physical font height (mm) and PDP area measurement.
4. **PostgreSQL & Task Queue Migration:** Migrate persistence to PostgreSQL and offload heavy OCR workloads to Celery/Redis background queues.