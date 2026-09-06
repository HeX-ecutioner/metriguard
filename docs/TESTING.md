# MetriGuard Testing & Quality Assurance Guide

## 1. Testing Goals
The goal of the **MetriGuard** test suite is to guarantee system correctness, evidence integrity, single-image lifecycle contracts, and deterministic compliance rule execution under problem statement **SIH26034**.

## 2. Testing Strategy
- **Backend Unit & Integration Testing:** Pytest suite testing models, database CRUD, storage sanitization, OCR preprocessor, regex pattern extractor, and codified LMR 2011 rule engine.
- **Frontend Component & Lifecycle Testing:** Vitest + React Testing Library suite verifying UI state transitions, file upload dropzone, progress tracking, manual review modal, and inspection history dashboard.
- **Single-Image Lifecycle Invariant Testing:** Database and API layer tests enforcing strict 1:1 relationships between inspection sessions and uploaded package images.
- **Verification Scripts & Live Smoke Testing:** End-to-end verification script ([`verify_setup.ps1`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/verify_setup.ps1)) and live API smoke test ([`backend/smoke_test.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/smoke_test.py)).

## 3. Test Categories Matrix

| Category | Framework / Tool | Test Directory / Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Rules** | Pytest | `backend/tests/` | Rule evaluation, regex extraction, DB models, storage security. |
| **Backend API & E2E** | Pytest + FastAPI TestClient | `backend/tests/test_api.py`, `test_e2e_workflow.py` | HTTP route validation, multipart uploads, status overrides. |
| **Frontend UI Components** | Vitest + React Testing Library | `frontend/src/components/*.test.tsx` | Drag-and-drop uploader, dashboard table, detail views. |
| **System Verification** | PowerShell | `powershell -File .\verify_setup.ps1` | Environment, dependencies, migrations, pytest, vitest, build. |
| **Live API Smoke Test** | Python | `python backend/smoke_test.py` | Live HTTP verification against running backend server. |

## 4. Mandatory Lifecycle Invariant Case Requirements

The test suite explicitly tests and enforces the following 10 lifecycle invariants:

1. **Selecting an Image Locally Creates No Database Record:**
   - Selecting a file in `ImageUpload.tsx` renders local preview state without triggering HTTP network requests or DB row creation ([`ImageUpload.test.tsx`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/src/components/ImageUpload.test.tsx)).
2. **Starting an Inspection Creates Exactly One Inspection ID:**
   - Clicking "Start Inspection" sends a single `POST /api/v1/inspections` request creating exactly one `Inspection` database entry ([`test_lifecycle_invariants.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_lifecycle_invariants.py)).
3. **One Inspection Cannot Receive a Second Image:**
   - Attempting to upload a second image to an existing inspection ID is rejected by the backend with **HTTP 409 Conflict** and enforced via database unique constraint `uq_package_images_inspection_id` ([`test_lifecycle_invariants.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_lifecycle_invariants.py)).
4. **Uploading Another Image Starts a New Inspection:**
   - Clicking "Upload another image" clears all active state, resets inspection ID to `null`, and returns to IDLE state so the next upload creates a completely independent inspection session ([`ImageUpload.test.tsx`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/src/components/ImageUpload.test.tsx)).
5. **Previous Results Do Not Appear Under New Inspection:**
   - Frontend state reset guarantees old extractions, bounding boxes, or violation cards do not leak into subsequent inspection sessions ([`ImageUpload.test.tsx`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/src/components/ImageUpload.test.tsx)).
6. **Canceling Before Upload Creates No Record:**
   - Clicking "Cancel" on selected image resets uploader to IDLE state without making API calls ([`ImageUpload.test.tsx`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/src/components/ImageUpload.test.tsx)).
7. **Stale Asynchronous Response Protection:**
   - Frontend requests include request token tracking to discard responses from cancelled or stale uploads ([`ImageUpload.tsx`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/src/components/ImageUpload.tsx)).
8. **Failed Processing Does Not Display False Compliance:**
   - Unhandled processing errors or corrupted image bytes route the inspection outcome directly to `FAILED` or `MANUAL_REVIEW`, never `COMPLIANT` ([`test_failure_cases.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_failure_cases.py)).
9. **Low-Confidence or Missing Evidence Produces MANUAL_REVIEW:**
   - Extraction confidence below `0.70` or missing mandatory fields automatically flag the inspection for `MANUAL_REVIEW` ([`test_rules_foundation.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rules_foundation.py)).
10. **Evidence & Bounding Box Requirement:**
    - Every reported violation includes exact OCR text evidence, bounding box coordinates `[x_min, y_min, x_max, y_max]`, or an explicit explanation if unreadable ([`test_rule_engine.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests/test_rule_engine.py)).

## 5. How to Run Each Test Category

### 5.1 Run Complete Backend Pytest Suite
```ps
cd backend
.venv\Scripts\pytest tests -v
```

### 5.2 Run Frontend Vitest Suite
```ps
cd frontend
npm test -- --run
```

### 5.3 Run Full System Environment & Test Verification Script
```haskell
powershell -ExecutionPolicy Bypass -File .\verify_setup.ps1
```

### 5.4 Run Live API Smoke Test
*(Requires running backend server on http://127.0.0.1:8000)*
```haskell
backend\.venv\Scripts\python backend\smoke_test.py
```

## 6. Inventory of Existing Backend & Frontend Test Files

### Backend Test Files ([`backend/tests/`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/tests))
1. `test_rules_foundation.py` - Core test suite for all 6 codified LMR 2011 compliance rules (pass, fail, exemption, low confidence, ambiguous scenarios).
2. `test_declaration_extraction.py` - Regex pattern matching tests across MRP, Net Qty, Dates, Entity, Consumer Care, and USP.
3. `test_lifecycle_invariants.py` - Single-image lifecycle contract and 1:1 database unique constraint tests.
4. `test_e2e_workflow.py` - Complete orchestration flow from image upload to rule output generation.
5. `test_upload_workflow.py` - Image byte validation, MIME checks, size limits, and storage file key sanitization.
6. `test_failure_cases.py` - Corrupted file, invalid byte, and OCR exception handling tests.
7. `test_ocr_service.py` - PaddleOCR and MockOCR provider unit tests.
8. `test_dashboard_api.py` - Dashboard stats endpoint, top violation aggregation, and filter query tests.
9. `test_api.py` - FastAPI route tests for creation, retrieval, review, and deletion.
10. `test_database.py` - SQLAlchemy ORM schema and CRUD operation tests.
11. `test_models.py` - Pydantic schema validation tests.
12. `test_storage.py` - Storage directory creation and path traversal prevention tests.
13. `test_rule_engine.py` - Rule engine registry and execution tests.

### Frontend Test Files ([`frontend/src/components/`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/src/components))
1. `ImageUpload.test.tsx` - Tests file dropzone, image selection, upload progress, lifecycle reset, and manual review editor.
2. `Dashboard.test.tsx` - Tests dashboard metric cards, search filter, status filter dropdown, and historical inspection table.

## 7. Known Testing Gaps
- **Real-World High Resolution Image Dataset:** Test suite primarily uses synthesized test images and mock bounding boxes. Benchmark evaluation against thousands of real retail packaging photos is planned.
- **Visual Regression Testing:** Automated visual snapshot testing (e.g. Playwright / Percy) for canvas bounding box overlays is not currently implemented.
- **Load / Stress Testing:** Performance stress testing under concurrent multi-user load (e.g. Locust / K6) is not currently implemented.

## 8. Release-Readiness Checklist
- [x] All 132 backend Pytest cases pass with 100% pass rate.
- [x] All 11 frontend Vitest component tests pass cleanly.
- [x] Frontend ESLint (`npm run lint`) reports 0 errors and 0 warnings.
- [x] Frontend TypeScript build (`npm run build`) compiles cleanly without errors.
- [x] Database migrations (`alembic upgrade head`) execute cleanly.
- [x] Environment verification script (`verify_setup.ps1`) passes all checks.
- [x] Live API smoke test script (`smoke_test.py`) passes all steps against running server.