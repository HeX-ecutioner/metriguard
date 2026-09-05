# Native Windows Development Setup Guide (Docker-Free)

MetriGuard is built to run 100% natively on Windows using native Python, Node.js, and local file-based storage. Docker, Docker Desktop, and container orchestration tools are **not required** and are not used anywhere in the core workflow.

---

## 1. System Prerequisites

Ensure the following runtimes are installed directly on Windows:

| Requirement | Minimum Version | Installation Verification |
| :--- | :--- | :--- |
| **Python** | 3.11+ (64-bit) | `python --version` |
| **Node.js** | v18+ | `node --version` |
| **npm** | v9+ | `npm --version` |
| **PowerShell** | 5.1+ or 7+ | `$PSVersionTable.PSVersion` |

> [!NOTE]
> Ensure **Python** and **Node.js** are added to your Windows `PATH` during installation.

---

## 2. Architecture Overview (Native Windows)

- **Frontend**: React 19 + TypeScript + Vite running locally on `http://localhost:5173`.
- **Backend**: FastAPI + Uvicorn running in a dedicated Python virtual environment (`backend/.venv`) on `http://localhost:8000`.
- **Database**: SQLite using `aiosqlite` and SQLAlchemy 2.0 with the database file stored locally under `backend/data/metriguard.db`.
- **Database Migrations**: Tracked versioned migrations via Alembic configured for SQLite (with batch mode enabled).
- **File Storage**: Local filesystem storage abstraction under `backend/storage/` (pluggable for future S3/MinIO drivers).
- **AI / Computer Vision**: Local OpenCV (`opencv-python-headless`) and PaddleOCR/Tesseract with fallback mock data when native binary OCR engines are not present.

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
3. Install dependencies from `requirements.txt` into the virtual environment.
4. Run Alembic migrations to initialize `backend/data/metriguard.db`.
5. Install frontend packages in `frontend/node_modules` via `npm install`.
6. Launch the Backend API on port 8000.
7. Launch the Frontend UI on port 5173.

---

## 4. Manual Step-by-Step Setup (Separate Terminals)

For everyday development, run the frontend and backend in separate terminal windows.

### Terminal 1: Backend Setup & Execution

1. Open PowerShell and navigate to the `backend` directory:
   ```powershell
   cd backend
   ```

2. Create a Python virtual environment (first time only):
   ```powershell
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(If PowerShell gives an execution policy error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

4. Install backend dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. (Optional) Install local OCR libraries:
   ```powershell
   pip install -r requirements-ocr.txt
   ```
   *Note: If Tesseract or PaddleOCR is not installed, MetriGuard automatically uses the simulated mock extractor so you can continue development without blockers.*

6. Apply database migrations:
   ```powershell
   alembic upgrade head
   ```

7. Start the FastAPI backend with auto-reload:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

- **API Base URL**: `http://127.0.0.1:8000`
- **Health Check**: `http://127.0.0.1:8000/health`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

### Terminal 2: Frontend Setup & Execution

1. Open a second PowerShell window and navigate to the `frontend` directory:
   ```powershell
   cd frontend
   ```

2. Install dependencies locally (first time only):
   ```powershell
   npm install
   ```

3. Start the Vite development server:
   ```powershell
   npm run dev
   ```

- **Frontend Application**: `http://localhost:5173`

The frontend automatically proxies `/api` requests to `http://127.0.0.1:8000`.

---

## 5. Environment Configuration

### Backend (`backend/.env`)
Copy `backend/.env.example` to `backend/.env` (defaults are already configured for local execution):

```env
HOST=127.0.0.1
PORT=8000
DEBUG=True

# Local SQLite database path
DATABASE_URL=sqlite+aiosqlite:///./data/metriguard.db

# Storage configuration
STORAGE_TYPE=local
STORAGE_DIR=./storage

# AI Extractor Toggle (set to true to use mock data for instant testing)
USE_MOCK_EXTRACTOR=false
```

### Frontend (`frontend/.env`)
Copy `frontend/.env.example` to `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

---

## 6. Database Migrations (Alembic)

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

SQLite files are saved under `backend/data/metriguard.db` and are excluded from git.

---

## 7. Storage Abstraction

Uploaded inspection images are handled via the `StorageService` interface defined in `backend/app/services/storage.py`.

- In native Windows development, files are saved locally to `backend/storage/<uuid>_<filename>`.
- The storage directory is created automatically on first run and is excluded from git.
- If S3 or MinIO cloud storage is needed in the future, a new subclass of `StorageService` can be implemented without changing the core inspection logic.

---

## 8. Running Automated Tests

### Backend Tests
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests
```

### Frontend Tests & Type Checking
```powershell
cd frontend
npm run lint
npm run build
npm test
```

---

## 9. Automated Setup Verification

To verify that your entire environment is configured correctly:

```powershell
.\verify_setup.ps1
```

This script checks:
- Python and Node.js installation
- `.venv` creation and package installation
- SQLite database initialization and Alembic migrations
- Local storage directory readiness
- Backend and frontend automated tests
