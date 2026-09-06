# Changelog

All notable changes to the MetriGuard project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

> **Notice**: MetriGuard (SIH26034) by team **AlgoForge** is an AI-assisted packaged-commodity compliance inspection prototype. It is designed for automated regulatory assistance and proof-of-concept verification under the Legal Metrology (Packaged Commodities) Rules, 2011. It is **not** a certified legal-compliance authority or official enforcement tool.

## [Unreleased]

### Added
- **Single-Image Inspection Invariant**: Enforced a one-to-one constraint between inspection sessions and uploaded package images at both the database level (`PackageImage.inspection_id` unique constraint) and service layer.
- **5-State Frontend Inspection Lifecycle**: Introduced explicit state transitions in `ImageUpload.tsx`:
  - `IDLE`: Displays dropzone and optional product name input.
  - `IMAGE_SELECTED`: Renders local client-side preview with metadata (filename, size) before making any server requests.
  - `PROCESSING`: Triggered only upon clicking "Start Inspection", executing session creation and upload.
  - `COMPLETED`: Read-only display of inspection results and evidence.
  - `ERROR`: Displays validation or API error states with retry options.
- **Pre-Upload Cancellation**: Added a "Cancel" button in `IMAGE_SELECTED` state that clears the local file selection and returns to `IDLE` with zero backend calls or database rows created.
- **Duplicate Upload Guard**: Configured backend to reject secondary image upload attempts to an active or completed inspection session with `HTTP 409 Conflict`.
- **Stale Response Protection**: Implemented request token tracking (`activeRequestId`) in the frontend to ignore callbacks from abandoned or cancelled processing requests.
- **Alembic Database Migration 003**: Added `003_one_image_per_inspection.py` migration script to enforce the unique index `ix_package_images_inspection_id` while automatically normalizing legacy multi-image records into isolated single-image sessions without data loss.
- **OCR Text Recognition Pipeline**: Integrated local PaddleOCR recognition with OpenCV pre-processing and CPU fallback configuration (`enable_mkldnn=False`) to prevent Windows x64 PIR executor crashes.
- **13 Declaration Types Extraction**: Implemented deterministic pattern extraction for mandatory Legal Metrology fields (MRP, Net Quantity, Manufacturer/Packer/Importer, Date of Manufacture/Packing, Consumer Care, Unit Sale Price, etc.).
- **Deterministic Rule Engine Foundation**: Codified 6 prototype rules under Legal Metrology (Packaged Commodities) Rules, 2011 with versioned rule evaluation and severity mapping (`CRITICAL`, `ERROR`, `WARNING`, `INFO`).
- **Evidence-Backed Findings**: Attached visual bounding box coordinates, line text references, and confidence scores to every detected violation.
- **Dashboard & Analytics UI**: Built responsive React dashboard displaying summary metrics (Total, Compliant, Non-Compliant, Manual Review), top violation statistics, filterable history table, and detailed inspection report views.
- **Native Windows Setup & Verification**: Added `start.ps1`, `start.bat`, and `verify_setup.ps1` for one-click environment validation and dual-server startup on Windows 10/11.

### Changed
- **"Upload Another Image" Workflow**: Updated `ImageUpload.tsx`, `App.tsx`, and `ResultsView.tsx` so clicking "Upload another image" cleanly resets `activeInspection` to `null` and returns the UI to `IDLE`, guaranteeing that subsequent uploads create a brand-new inspection ID rather than stacking results onto prior sessions.
- **Results View Rendering**: Updated `ResultsView.tsx` to render strictly the primary image and findings associated with the current inspection session.
- **Environment Configuration Guidance**: Updated documentation and setup guides to specify that `backend/.env` is optional for local development (falling back to built-in defaults) and used for developer overrides.

### Fixed
- **Inspection Session Stacking Bug**: Resolved issue where selecting a new image after an inspection reused the previous `inspectionId`, causing multiple images and conflicting declaration sets to append to the same database row.
- **Validation Error Handling**: Ensured invalid file uploads (e.g. unsupported extension or corrupt bytes) return `HTTP 400 Bad Request` without transitioning the inspection status to `PROCESSING` or corrupting the session.
- **PaddleOCR Windows x64 PIR Crash**: Fixed `ConvertPirAttribute2RuntimeAttribute` crash on Windows CPU by explicitly setting `FLAGS_use_mkldnn=0`.

### Security
- **Path Traversal Protection**: Sanitized uploaded file names using standard Path abstractions to prevent relative path traversal attacks during file storage.
