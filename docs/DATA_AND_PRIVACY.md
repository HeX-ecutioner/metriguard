# MetriGuard Data Handling & Privacy Policy

## 1. Document Purpose & Scope
This document details the data collection, processing, storage, deletion, and privacy boundaries for **MetriGuard** (developed by team **AlgoForge** for problem statement **SIH26034**).

## 2. Prototype Status & Privacy Disclaimer
> [!WARNING]
> **MetriGuard is a demonstration prototype system.**
> - It is **not** audited for GDPR, HIPAA, or ISO 27001 compliance.
> - Images uploaded to the system are stored unencrypted on the host server disk.
> - **Do NOT upload images containing personally identifiable information (PII), confidential personal media, or private financial/medical records.**

## 3. Data Received by the Application
MetriGuard accepts the following data inputs from client applications:
1. **Package Label Images:** Uploaded image files in JPEG, PNG, or WEBP formats up to 10 MB in size via `POST /api/v1/inspections/{id}/images`.
2. **Metadata & Notes:** Optional product name strings (`product_name`) and inspector notes (`notes`) provided via `POST /api/v1/inspections`.
3. **HTTP Metadata:** Standard web server request headers (IP address, User-Agent, request timestamp).

## 4. Extracted Data
During the automated 5-step inspection pipeline, the backend extracts:
- **Raw OCR Text:** Text line strings, line bounding box coordinates `[x_min, y_min, x_max, y_max]`, and optical detection confidence scores.
- **Parsed Declarations:** 13 Legal Metrology declaration fields (Maximum Retail Price, Net Quantity, Dates, Manufacturer/Packer/Importer Entity Name & Address, Consumer Care Contact, Unit Sale Price).
- **Rule Findings:** Pass/fail status, evidence text snippets, and severity metrics for codified compliance rules.

## 5. Storage Location & Persistence
- **Image File Storage:** Saved locally on the host server filesystem disk at `backend/data/uploads/` ([`storage.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/storage.py)). Filenames are prepended with random UUID prefixes (`uuid4().hex`) to prevent collisions and path traversal.
- **Relational Persistence:** Metadata, OCR results, parsed declarations, and rule evaluations are stored in a local SQLite database at `backend/data/metriguard.db`.
- **Encryption Status:** Data is stored **unencrypted at rest** on standard local disk storage.

## 6. Data Retention Period
- **Current Behavior:** Data is retained **indefinitely** on the server disk and database until explicitly deleted by a user or administrator.
- **Automated Retention:** There is **no automated TTL (time-to-live) expiry job** or automated data purging in the current prototype.

## 7. Third-Party Data Transmission
- **Local OCR Engine (Default):** Native PaddleOCR (`paddleocr`) and `MockOCRProvider` execute **100% locally on the host server**. Uploaded images and text are **not** transmitted to external third-party cloud OCR APIs.
- **Optional AI Extractor Module:** An optional fallback module ([`ai_extractor.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/ai_extractor.py)) supports calling cloud LLM vision APIs (Gemini/OpenAI) if API keys are explicitly configured. In standard local execution (`USE_MOCK_EXTRACTOR=false` with default config), cloud vision API transmission is **disabled**.

## 8. Logging & Diagnostic Data
- Application logs are written to standard output (stdout/stderr) via Python's `logging` module.
- Logs include inspection IDs, original filenames, file sizes, image dimensions, processing durations, and execution status messages.
- Raw image binary bytes are **never** logged to text log files.

## 9. Data Deletion Protocol
Users can delete an inspection record and its associated image file:
- **API Deletion:** Executing `DELETE /api/v1/inspections/{id}` purges the inspection session, child OCR results, declarations, and rule evaluations from SQLite, and physically deletes the image file from `backend/data/uploads/`.
- **Manual Disk Purge:** Deleting `backend/data/metriguard.db` and clearing files in `backend/data/uploads/` completely resets the application state.

## 10. Prohibited Content
Users must **NOT** upload:
- Clear photos of human faces or personal identification documents (Aadhaar, Passport, Driver's License).
- Personal residential addresses, private personal phone numbers, or personal email addresses.
- Confidential unreleased trade secret artwork or proprietary financial records.

## 11. Privacy Controls Summary

### Implemented Privacy Controls:
- [x] **Filename Sanitization:** Uploaded filenames are sanitized with UUID prefixes (`uuid4().hex`) to remove sensitive original file naming metadata.
- [x] **Path Traversal Protection:** Image file paths are validated using `is_relative_to(UPLOADS_DIR)` to prevent unauthorized filesystem access.
- [x] **Local Processing Option:** Native PaddleOCR processes package images locally without external cloud API transmission.
- [x] **Explicit Record Deletion:** API endpoint (`DELETE /api/v1/inspections/{id}`) supports purging database records and backing disk storage files.

### Missing Privacy Controls (Planned Improvements):
- [ ] **Authentication & Access Authorization:** Currently, image URL endpoints (`/api/v1/inspections/{id}/images/{img_id}/file`) are unauthenticated.
- [ ] **Automated Expiry Retention TTL:** Automated purge script for deleting demonstration records older than $N$ days.
- [ ] **Encryption at Rest:** Disk-level or application-level encryption for stored packaging images and SQLite database.
- [ ] **Automated Face / PII Redaction:** Automatic blurring of detected human faces or non-packaging PII text before saving images to disk.
