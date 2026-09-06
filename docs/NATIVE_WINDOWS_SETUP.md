# Native Windows Development Setup Guide (Docker-Free)

MetriGuard is built to run 100% natively on Windows using native Python, Node.js, and local file-based storage. Docker, Docker Desktop, and container orchestration tools are **not required** and are not used anywhere in the core workflow.

---

## 1. System Prerequisites

Ensure the following runtimes are installed directly on Windows:

| Requirement | Minimum Version | Installation Verification |
| :--- | :--- | :--- |
| **Python** | 3.11+ (64-bit) | `py --version` or `python --version` |
| **Node.js** | v18+ | `node --version` |
| **npm** | v9+ | `npm --version` |
| **PowerShell** | 5.1+ or 7+ | `$PSVersionTable.PSVersion` |

> [!NOTE]
> Ensure **Python** and **Node.js** are added to your Windows `PATH` during installation.

---

## 2. Architecture Overview (Native Windows)

- **Frontend**: React 19 + TypeScript + Vite running locally on `http://localhost:5173`.
- **Backend**: FastAPI + Pydantic Settings + Uvicorn running in a dedicated Python virtual environment (`backend/.venv`) on `http://localhost:8000`.
- **Database**: SQLite using standard SQLAlchemy 2.0 with Python's built-in `sqlite3` driver. The database file is stored locally at `backend/data/metriguard.db`.
- **Database Migrations**: Versioned migrations via Alembic.
- **File Storage**: Local filesystem abstraction managing `backend/storage/`, `backend/storage/uploads/`, and `backend/storage/reports/`.
- **AI Extraction**: Graceful development mock extractor by default, with optional local OCR support (PaddleOCR / Tesseract) when installed.

---

## 3. Quick Start (Automatic Setup)

From the project root directory, run the PowerShell startup script:

```powershell
.\start.ps1
```

Or using Command Prompt / batch file:

```cmd
start.bat
```

This will:
1. Verify Python and Node.js are available.
2. Initialize `backend/.venv` if not already present.
3. Install skeleton dependencies from `backend/requirements.txt` into the virtual environment.
4. Run Alembic migrations to initialize `backend/data/metriguard.db`.
5. Install frontend packages in `frontend/node_modules` via `npm install`.
6. Launch the Backend API on port 8000.
7. Launch the Frontend UI on port 5173.

---

## 4. Manual Step-by-Step Setup (Separate Terminals)

For everyday development, you can run the frontend and backend in separate terminal windows.

### Terminal 1: Backend Setup & Execution (PowerShell)

Run the following commands in PowerShell from the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

#### Troubleshooting PowerShell Script Execution Policy:

If PowerShell displays an error such as:
> *cannot be loaded because running scripts is disabled on this system*

Resolve it for your **current user account only** (without altering system-wide policy):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Alternatively, bypass the policy solely for your current PowerShell window:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

### Terminal 2: Frontend Setup & Execution

Open a second PowerShell window and navigate to the `frontend` directory:

```powershell
cd frontend
npm install
npm run dev
```

- **Frontend Application**: `http://localhost:5173`
- **Backend API**: `http://127.0.0.1:8000`
- **Health Check**: `http://127.0.0.1:8000/health` (Returns `{"status": "ok"}`)
- **Detailed Diagnostics**: `http://127.0.0.1:8000/health/detail`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

## 5. Environment Configuration

### Backend (`backend/.env`)

Configuration is managed via `backend/app/core/config.py` using `pydantic-settings`.
Copy `backend/.env.example` to `backend/.env`:

```env
APP_ENV=development
DATABASE_URL=sqlite:///./data/metriguard.db
STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=10
CORS_ORIGINS=http://localhost:5173

# Server settings
HOST=127.0.0.1
PORT=8000

# AI Extractor Toggle (Set to true to use mock data for instant testing without OCR)
USE_MOCK_EXTRACTOR=false
```

No secrets or passwords are required for local development.

---

## 6. Directory Structure Created Automatically

The backend automatically creates the following local directories on startup:

- `backend/data/` - Holds the SQLite database file (`metriguard.db`).
- `backend/storage/` - Base folder for local file storage abstraction.
- `backend/storage/uploads/` - Incoming commodity package images uploaded for inspection.
- `backend/storage/reports/` - Generated PDF/JSON compliance audit reports.

All database files and uploads are excluded from git tracking.

---

## 7. Backend Verification Script

To verify that your backend environment, dependencies, database, storage directories, and health endpoint are properly configured:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python verify_backend.py
```

This verification script checks:
1. **Python Version**: Confirms Python $\ge 3.11$.
2. **Required Packages**: Confirms all 9 skeleton dependencies (`fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic`, `pydantic-settings`, `python-multipart`, `pytest`, `httpx`).
3. **Database Connection**: Confirms live SQLite connectivity via SQLAlchemy.
4. **Writable Storage**: Confirms `data/`, `storage/`, `storage/uploads/`, and `storage/reports/` exist and are writable.
5. **Health Endpoint**: Verifies `GET /health` returns HTTP 200 with `{"status": "ok"}`.

---

## 8. Database Migrations (Alembic)

All schema changes are tracked with Alembic inside `backend/`.

- **Apply all migrations**:
  ```powershell
  cd backend
  .\.venv\Scripts\Activate.ps1
  alembic upgrade head
  ```

- **Create a new migration after editing SQLAlchemy models**:
  ```powershell
  alembic revision --autogenerate -m "describe_changes_here"
  ```

- **View migration history**:
  ```powershell
  alembic history
  ```

---

## 9. Running Automated Tests

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
