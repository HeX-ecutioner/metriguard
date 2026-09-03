# MetriGuard

AI-Assisted Legal Metrology Compliance Inspection Platform for Packaged Commodities.

MetriGuard automates the verification of mandatory declarations under the **Legal Metrology (Packaged Commodities) Rules, 2011**. It combines AI text extraction (with fallback mock extraction for local dev) and a deterministic regulatory rule engine to detect compliance violations in real time.

---

## Architecture Overview

- **Frontend**: React 19 + TypeScript + Vite + Glassmorphic UI Design System.
- **Backend**: FastAPI + Pydantic v2 + Uvicorn.
- **Rules Engine**: Deterministic regex-based validator enforcing Legal Metrology Rules:
  - **Rule 6(1)(e)**: Retail Sale Price (MRP) declaration.
  - **Rule 6(1)(c)**: Net quantity declaration (e.g. g, kg, ml, L).
  - **Rule 6(1)(a)**: Manufacturer / Packer / Importer name and address.
  - **Rule 6(1)(d)**: Month and year of manufacture or packing.
- **AI Extraction**: PaddleOCR (in Docker/production) with development mock extraction fallback for instant local testing.
- **Database (Optional)**: PostgreSQL with SQLAlchemy 2.0 async engine.

---

## Quick Start (Local Run — No Docker Required)

### 1. Prerequisites
- **Node.js**: v18+ installed
- **Python**: 3.11 or 3.12 installed

### 2. Backend Setup
1. Navigate to the backend directory:
   ```powershell
   cd backend
   ```
2. (Optional) Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Start the FastAPI server:
   ```powershell
   python -m uvicorn app.main:app --reload --port 8000
   ```
   *The backend will start at `http://127.0.0.1:8000`.*
   *API documentation (Swagger UI) is available at `http://127.0.0.1:8000/docs`.*

### 3. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```powershell
   cd frontend
   ```
2. Start the Vite development server:
   ```powershell
   npm run dev
   ```
   *The frontend will open at `http://localhost:5173`.*

---

## Docker Setup (Optional)

When Docker Desktop is installed and running:
```powershell
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

---

## Running Tests

### Backend Unit & Integration Tests:
```powershell
python -m pytest backend/tests
```

### Frontend Linting & Build:
```powershell
cd frontend
npm run lint
npm run build
```
