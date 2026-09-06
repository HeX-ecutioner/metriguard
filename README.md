# MetriGuard

AI-Assisted Legal Metrology Compliance Inspection Platform for Packaged Commodities (SIH26034).

MetriGuard automates the verification of mandatory declarations under the **Legal Metrology (Packaged Commodities) Rules, 2011**. It combines local OCR text extraction, deterministic declaration parsing across 13 declaration types, and a reproducible regulatory rule engine to detect compliance violations in real time.


## 1. Prerequisites

Before setting up MetriGuard on Windows, ensure the following software is installed and available on your system `PATH`:

- **Operating System**: Windows 10 or Windows 11 (x64)
- **Python**: Version `3.11` or `3.12` ([python.org](https://www.python.org/downloads/windows/))
  - *Ensure "Add python.exe to PATH" is checked during installation.*
- **Node.js & npm**: Node.js `v18+` or `v20+` LTS ([nodejs.org](https://nodejs.org/))
- **PowerShell**: PowerShell 5.1+ (built into Windows) or PowerShell 7+

## 2. Backend Setup

1. Open PowerShell and navigate to the project `backend` directory:
   ```ps
   cd backend
   ```

2. Create a dedicated Python virtual environment:
   ```ps
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```ps
   .\.venv\Scripts\Activate.ps1
   ```
   *(If script execution is blocked, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

4. Install backend dependencies:
   ```ps
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Verify environment variables in `backend/.env`:
   ```sh
   APP_ENV=development
   DATABASE_URL=sqlite:///./data/metriguard.db
   STORAGE_PATH=./storage
   MAX_UPLOAD_SIZE_MB=10
   CORS_ORIGINS=http://localhost:5173
   HOST=127.0.0.1
   PORT=8000
   ```

## 3. Frontend Setup

1. Open PowerShell and navigate to the `frontend` directory:
   ```ps
   cd frontend
   ```

2. Install npm dependencies:
   ```ps
   npm install
   ```

3. Verify environment configuration:
   The frontend defaults to connecting to the local backend at `http://127.0.0.1:8000`. If you wish to override this, configure `VITE_API_URL` in `frontend/.env`.

## 4. Database Setup

MetriGuard uses a persistent SQLite database stored locally under `backend/data/metriguard.db`. Schema revisions are versioned and managed using **Alembic**.

1. Navigate to the `backend` directory with the virtual environment activated:
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   ```

2. Apply all database migrations to head:
   ```powershell
   alembic upgrade head
   ```

3. Verify current migration status:
   ```powershell
   alembic current
   ```
   Expected output: `002_inspection_workflow_models (head)`

## 5. Running the Application

### Option A: One-Click Launcher (Recommended)
From the root workspace directory, run the native launcher script:
```powershell
.\start.ps1
```
*(Alternatively, double-click `start.bat` from Windows File Explorer).*

This script automatically verifies dependencies, initializes directories, applies database migrations, and launches both backend and frontend servers in separate background jobs.

- **Frontend UI**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### Option B: Manual Execution (Two Terminals)

**Terminal 1 (Backend):**
```ps
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```ps
cd frontend
npm run dev
```

## 6. Running Tests

### Automated Environment Verification
Run the diagnostic setup validation script from the root workspace:
```ps
powershell -ExecutionPolicy Bypass -File .\verify_setup.ps1
```

### Backend Tests (`pytest`)
Runs all 152 unit, integration, regulatory rule engine, orchestrator, and failure-case tests:
```ps
cd backend
.\.venv\Scripts\pytest tests -q
```

### Live API Smoke Tests
Executes end-to-end live HTTP requests against the running backend (health check, dashboard stats, package upload, OCR extraction, rule evaluation, and original image retrieval):
```powershell
backend\.venv\Scripts\python backend\smoke_test.py
```

### Frontend Tests, Linting & Build

```ps
cd frontend

# 1. Run Vitest component tests (Dashboard, Upload, Detail)
npm test -- --run

# 2. Run ESLint checks
npm run lint

# 3. Verify TypeScript type checking and production build
npm run build
```

## 7. Troubleshooting

### 1. PaddleOCR oneDNN Error on Windows x64
- **Symptom**: `(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`
- **Root Cause**: PaddlePaddle 3.x CPU inference previously defaulted to oneDNN PIR translation which is incomplete on Windows.
- **Fix**: The application automatically sets `enable_mkldnn=False` and `FLAGS_use_mkldnn=0` in `backend/app/services/ocr/paddle_provider.py`. PaddleOCR executes cleanly on standard CPU.

### 2. PowerShell Script Execution Policy Blocked
- **Symptom**: `File ...\Activate.ps1 cannot be loaded because running scripts is disabled on this system.`
- **Fix**: In your PowerShell session, run:
  ```ps
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 3. Alembic "Path doesn't exist: alembic"
- **Symptom**: Running `alembic current` from root fails to locate the scripts folder.
- **Fix**: Always run Alembic commands directly from the `backend/` directory:
  ```ps
  cd backend
  .\.venv\Scripts\alembic upgrade head
  ```

### 4. Windows Console Unicode Encoding (`\u2713`)
- **Symptom**: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`.
- **Fix**: Windows console uses code page 1252 by default. Set UTF-8 encoding before running CLI tools:
  ```ps
  $env:PYTHONIOENCODING="utf-8"
  ```

## 8. Resetting Local Development Data

If you need to reset all inspections, uploaded images, and database records back to a fresh state:

1. Stop any running backend and frontend processes (`Ctrl + C`).
2. Delete the SQLite database file and uploads directory:
   ```ps
   Remove-Item -Force "backend\data\metriguard.db" -ErrorAction SilentlyContinue
   Remove-Item -Recurse -Force "backend\storage\uploads\*" -ErrorAction SilentlyContinue
   ```
3. Reapply database migrations from the `backend` directory:
   ```ps
   cd backend
   .\.venv\Scripts\alembic upgrade head
   ```
4. Restart the servers:
   ```ps
   cd ..
   .\start.ps1
   ```