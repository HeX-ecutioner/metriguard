# Contributing to MetriGuard

Thank you for your interest in contributing to **MetriGuard** by team **AlgoForge**!

## 1. Project Scope & Context

**MetriGuard** is an AI-assisted packaged-commodity compliance inspection prototype developed for **Smart India Hackathon (SIH26034)**. It automates the extraction and verification of mandatory declarations under the **Legal Metrology (Packaged Commodities) Rules, 2011** (LMR 2011).

> **Disclaimer**: This repository contains an academic research and hackathon proof-of-concept prototype. It is designed to assist human inspectors with automated evidence extraction and rule evaluation. It is **not** a legally certified compliance authority or official enforcement tool.

The core architecture prioritizes:
- **Explainability**: Every violation must link to a specific LMR 2011 rule clause.
- **Evidence-Backed Output**: All extractions attach visual bounding boxes and text snippets.
- **Reproducibility**: Deterministic rule evaluation over black-box decisions.
- **Safe Manual Review**: Ambiguities and OCR failures route strictly to `MANUAL_REVIEW` (never `COMPLIANT`).

## 2. Who Can Contribute

This repository is primarily maintained for the SIH26034 hackathon project by team AlgoForge. Guidelines provided here serve as reference for team members, reviewers, and potential external contributors wishing to fork or propose improvements to the prototype.

## 3. How to Fork and Clone

1. **Fork the Repository**: Click the **Fork** button at the top right of the GitHub repository page.
2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/SagnikMaitra/metriguard.git
   cd metriguard
   ```

## 4. Local Prerequisites

Ensure the following tools are installed on your system before setting up:

- **Operating System**: Windows 10/11 (x64) recommended, or Linux / macOS.
- **Python**: Version `3.11` or `3.12` (must be added to system `PATH`).
- **Node.js & npm**: Node.js `v18+` or `v20+` LTS.
- **PowerShell**: PowerShell 5.1+ or PowerShell 7+ (on Windows).

## 5. Local Setup

MetriGuard consists of a Python FastAPI backend and a React (Vite + TypeScript) frontend.

### Automated Verification Script (Windows)
From the root workspace directory, run:
```ps
powershell -ExecutionPolicy Bypass -File .\verify_setup.ps1
```
This script checks system dependencies, initializes local storage directories (`backend/storage/uploads`, `backend/storage/reports`), verifies database migrations, and runs tests.

## 6. Environment Configuration (Without Exposing Secrets)

The backend configuration is managed by `pydantic-settings` in `backend/app/core/config.py`.

- **Defaults**: The application ships with safe local defaults (`127.0.0.1:8000`, local SQLite database at `backend/data/metriguard.db`). Running without a `.env` file works out-of-the-box.
- **Optional Custom Overrides**: Copy the template in `backend/.env.example` to create `backend/.env`:
  ```bash
  cd backend
  cp .env.example .env
  ```
- **Security Rule**: Never commit `.env` files, API keys, passwords, or production secrets to Git. The `.env` file is listed in `.gitignore`.

## 7. How to Run the Frontend

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The UI will be accessible at [http://localhost:5173](http://localhost:5173).

---

## 8. How to Run the Backend

1. Navigate to the `backend` directory:
   ```ps
   cd backend
   ```
2. Create and activate a virtual environment:
   ```ps
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install backend dependencies:
   ```ps
   pip install -r requirements.txt
   ```
4. Apply database migrations:
   ```ps
   alembic upgrade head
   ```
5. Launch the FastAPI server using Uvicorn:
   ```ps
   python -m uvicorn app.main:app --reload --port 8000
   ```
   - **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - **Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **Health Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### One-Click Startup (Both Servers)
From the root workspace directory, run:
```bash
.\start.ps1
```

## 9. How to Run Tests

### Backend Unit & Integration Tests (Pytest)
From the root workspace directory or `backend/` directory:
```ps
# Run complete backend test suite
backend\.venv\Scripts\python.exe -m pytest backend/tests -v

# Run fast tests excluding heavy PaddleOCR initialization
backend\.venv\Scripts\python.exe -m pytest backend/tests -v -k "not test_ocr_service"
```

### Live API Smoke Tests
With the backend server running on port 8000:
```haskell
backend\.venv\Scripts\python.exe backend/smoke_test.py
```

### Frontend Tests (Vitest)
From the `frontend` directory:
```bash
cd frontend
npm test
```

## 10. Code Formatting and Linting

Use the project's actual linting and formatting commands prior to submitting code:

### Frontend (TypeScript / React)
```bash
cd frontend

# Run ESLint
npm run lint

# Run TypeScript type check & production build verification
npm run build
```

### Backend (Python)
If dev dependencies are installed (`pip install ruff mypy`):
```bash
cd backend
ruff check .
mypy app
```

## 11. Branch Naming Guidance

Name branches clearly based on the purpose of the change:

- `feature/<feature-name>` (e.g. `feature/unit-sale-price-rule`)
- `fix/<bug-description>` (e.g. `fix/single-image-lifecycle`)
- `docs/<topic>` (e.g. `docs/regulatory-rules-update`)
- `refactor/<scope>` (e.g. `refactor/ocr-provider-abstraction`)

## 12. Commit Message Guidance

Follow clear, imperative commit messages (Conventional Commits style preferred):

- `feat(rules): add rule LMR-2011-R06-1-DA for Unit Sale Price`
- `fix(lifecycle): enforce single-image constraint per inspection session`
- `docs(readme): clarify optional .env usage for local setup`
- `test(backend): add regression test for HTTP 409 duplicate upload rejection`

## 13. Pull Request Requirements

Before opening a Pull Request (PR):

1. **Verify All Tests Pass**: Run `verify_setup.ps1`, `pytest`, and `npm test`.
2. **Verify Type Check & Lint**: Run `npm run build` and `npm run lint` in `frontend/`.
3. **Database Migrations**: If modifying SQLAlchemy models in `backend/app/db/models.py`, generate and test a new Alembic migration (`alembic revision --autogenerate -m "description"`).
4. **Single-Image Invariant**: Ensure no changes break the invariant that one inspection session maps to exactly one package image.
5. **No Broken Contracts**: Ensure response schema formats in `backend/app/models/schemas.py` and `frontend/src/api/client.ts` remain synchronized.

## 14. Requirements for Changing Regulatory Rules

When modifying or adding rules under the Legal Metrology (Packaged Commodities) Rules, 2011:

1. **Rule Traceability**: Every rule must map explicitly to a codified clause in LMR 2011 (e.g. `LMR-2011-R06-1-A` through `E`).
2. **Rule Registry**: Register new rules in `backend/app/services/rules/registry.py`.
3. **Severity Classification**: Assign accurate severity levels (`CRITICAL`, `ERROR`, `WARNING`, `INFO`).
4. **Documentation**: Update [docs/REGULATORY_RULES.md](file:///c:/Users/Sagnik/Documents/GitHub%20repos/metriguard/docs/REGULATORY_RULES.md).
5. **Test Coverage**: Add unit tests in `backend/tests/test_rules_foundation.py` covering passing, failing, ambiguous, and exempt (e.g. wholesale or Rule 26 exemption) cases.

## 15. Requirements for Adding OCR or AI Behavior

1. **Local & Reproducible**: OCR recognition must rely on local processing (PaddleOCR / OpenCV).
2. **CPU Safety**: Ensure CPU execution settings (`FLAGS_use_mkldnn=0`) are preserved on Windows to prevent PIR executor crashes.
3. **Fail-Safe Routing**: OCR failures or unreadable images must route strictly to `MANUAL_REVIEW` (never `COMPLIANT`).
4. **Decoupled Architecture**: Keep computer vision and OCR extraction decoupled from regulatory decision logic.

## 16. Requirements for Evidence and Confidence Logic

1. **Bounding Box Reference**: All extracted declarations and detected violations must attach bounding box coordinates `(x, y, width, height)` where available.
2. **Confidence Scores**: Confidence values must be bounded between `0.0` and `1.0`.
3. **Low-Confidence Review**: Extractions falling below confidence threshold `0.5` must flag `MANUAL_REVIEW` rather than making authoritative compliance assertions.

## 17. Bug Report Guidance

When reporting a bug or edge-case failure:

1. **Environment Context**: Mention OS version, Python version, Node version, and database status.
2. **Reproduction Steps**: List exact step-by-step instructions to reproduce the issue.
3. **Expected vs Actual**: Describe what was expected to happen versus what actually occurred.
4. **Logs & Stack Traces**: Include full, un-truncated error logs from the terminal or browser console.

## 18. Security and Privacy Expectations

1. **No Sensitive Data**: Do not commit real personal data, private packaging documents, or confidential credentials.
2. **Path Sanitization**: Ensure file upload paths use sanitized filenames to prevent directory traversal.
3. **Input Validation**: All image uploads must pass MIME, extension, size (10MB max), and Pillow decoding checks before processing.

## 19. Prohibited Contributions

The following types of contributions will be rejected:

- **Fabricated Evidence**: Modifying rule engines or extractions to output fake bounding boxes or false compliance passes.
- **Hardcoded Secrets**: Committing passwords, secret keys, or local file paths.
- **Unsubstantiated Legal Claims**: Codifying regulatory rules that do not exist in the official Legal Metrology (Packaged Commodities) Rules, 2011 text.
- **Unlicensed Datasets**: Adding images, fonts, or code assets without appropriate open-source licenses or usage permissions.
