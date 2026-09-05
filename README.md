# MetriGuard

AI-Assisted Legal Metrology Compliance Inspection Platform for Packaged Commodities (SIH26034).

MetriGuard automates the verification of mandatory declarations under the **Legal Metrology (Packaged Commodities) Rules, 2011**. It combines AI text extraction (with fallback mock extraction for local dev) and a deterministic regulatory rule engine to detect compliance violations in real time.

---

## Architecture Overview (Native Windows)

- **Frontend**: React 19 + TypeScript + Vite + Glassmorphic UI Design System.
- **Backend**: FastAPI + Pydantic v2 + Uvicorn running in a local virtual environment (`backend/.venv`).
- **Rules Engine**: Deterministic regex-based validator enforcing Legal Metrology Rules:
  - **Rule 6(1)(e)**: Retail Sale Price (MRP) declaration.
  - **Rule 6(1)(c)**: Net quantity declaration (e.g., g, kg, ml, L).
  - **Rule 6(1)(a)**: Manufacturer / Packer / Importer name and address.
  - **Rule 6(1)(d)**: Month and year of manufacture or packing.
- **AI Extraction**: Local OCR (Tesseract / PaddleOCR) with automatic development mock extraction fallback.
- **Database**: SQLite with SQLAlchemy 2.0 async engine stored under `backend/data/metriguard.db`.
- **Database Migrations**: Tracked versioned migrations via Alembic.
- **Storage**: Local filesystem storage abstraction under `backend/storage/` (pluggable for future S3/MinIO).

---

## Quick Start (Local Windows)

### 1. Prerequisites
- **Python**: 3.11+ (installed and added to PATH)
- **Node.js**: v18+ with npm (installed and added to PATH)
- **PowerShell**: 5.1+ or 7+

### 2. One-Click Launch
Run the native PowerShell launcher:

```powershell
.\start.ps1
```

*(Alternatively, run `start.bat` from Command Prompt)*

- **Frontend UI**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`
- **Swagger Docs**: `http://localhost:8000/docs`

---

## Manual Setup (Separate Terminals)

### Terminal 1: Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2: Frontend

```powershell
cd frontend
npm install
npm run dev
```

---

## Health Check & Verification

MetriGuard exposes a health check endpoint at `/health` and `/api/v1/health` providing the status of the API, SQLite database, and storage system:

```powershell
curl http://127.0.0.1:8000/health
```

To run an automated full-environment verification check:

```powershell
.\verify_setup.ps1
```

---

## Running Automated Tests

### Backend Unit & Integration Tests:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests
```

### Frontend Tests, Linting & Build:
```powershell
cd frontend
npm run lint
npm run build
npm test
```

---

## Detailed Documentation

For a comprehensive guide on environment configuration, SQLite migrations, and troubleshooting on Windows, see [NATIVE_WINDOWS_SETUP.md](file:///c:/Users/Sagnik/Documents/GitHub%20repos/metriguard/docs/NATIVE_WINDOWS_SETUP.md).
