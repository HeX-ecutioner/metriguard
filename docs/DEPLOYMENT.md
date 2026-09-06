# MetriGuard Deployment Guide

## 1. Deployment Overview
This guide provides instructions for deploying **MetriGuard**, an AI-assisted packaged-commodity inspection system prototype.

The deployment model consists of:
- **FastAPI Backend:** Python 3.10+ ASGI service running Uvicorn.
- **React Frontend:** Static single-page application built using Vite and React 18.
- **Database:** Local SQLite database (`backend/data/metriguard.db`) managed via Alembic migrations.
- **Storage:** Local server disk storage for uploaded package images (`backend/data/uploads`).

## 2. Prototype Disclaimer & Supported Deployment Model
> [!IMPORTANT]
> **MetriGuard is a controlled demonstration prototype for SIH26034.**
> - It is **not** a production legal-certification system.
> - The primary deployment model is a **controlled demonstration server** or **native local station** running on Windows or Linux.

## 3. Prerequisites
- **Operating System:** Windows 10/11 x64 or Linux (Ubuntu 22.04+).
- **Python:** Python 3.10, 3.11, or 3.12.
- **Node.js:** Node.js v18.0.0+ and `npm` v9.0.0+.
- **OCR Engine Dependencies:** System-level dependencies for PaddleOCR or Tesseract OCR (if using live OCR inference; otherwise `MockOCRProvider` operates without extra binary dependencies).

## 4. Repository Preparation
Clone the repository and ensure clean working state:
```bash
git clone https://github.com/AlgoForge/metriguard.git
cd metriguard
```

## 5. Required Environment Variables

### Backend Configuration (`backend/.env`)

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Environment mode (`development` or `production`). |
| `DATABASE_URL` | `sqlite:///./data/metriguard.db` | SQLAlchemy connection string. |
| `STORAGE_PATH` | `./storage` | Directory path for image and report file storage. |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum allowed package image upload size in MB. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed frontend origins. |
| `HOST` | `127.0.0.1` | Network interface host binding for Uvicorn server. |
| `PORT` | `8000` | Port for backend Uvicorn server. |
| `USE_MOCK_EXTRACTOR` | `false` | Enable mock declaration extractor mode for testing. |
| `OCR_PROVIDER` | `auto` | OCR provider mode (`auto`, `paddle`, `mock`). |
| `OCR_CONFIDENCE_THRESHOLD` | `0.5` | Threshold for individual OCR line character confidence. |
| `OCR_MAX_IMAGE_DIMENSION` | `2400` | Max dimension to downscale image before OCR processing. |
| `OCR_TIMEOUT_SECONDS` | `30.0` | Timeout limit for single image OCR execution. |

### Frontend Configuration (`frontend/.env`)

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Base URL of the FastAPI backend service. |

## 6. Local Production-Like Testing (Native Windows Launcher)
To spin up both backend and frontend environments synchronously on Windows, run:
```ps
.\start.ps1
```
This script initializes Python `.venv`, installs dependencies, runs database migrations, and launches both development servers.

## 7. Backend Deployment Step-by-Step

1. **Navigate to Backend & Create Virtual Environment:**
   ```ps
   cd backend
   python -m venv .venv
   ```

2. **Activate Environment & Install Dependencies:**
   - **Windows:**
     ```haskell
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```
   - **Linux/macOS:**
     ```bash
     source .venv/bin/activate
     pip install -r requirements.txt
     ```

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and set values:
   ```bash
   cp .env.example .env
   ```

4. **Execute Database Migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start Production Uvicorn Server:**
   ```haskell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

## 8. Database Deployment
- **Default Database:** SQLite (`backend/data/metriguard.db`).
- **Persistence:** SQLite writes to local server disk. Ensure persistent disk storage if deploying on cloud virtual machines (e.g. AWS EC2, Azure VM, DigitalOcean Droplet).
- **Migration Command:** Run `alembic upgrade head` from the `backend/` directory whenever applying updates.

## 9. Image-Storage Configuration
- Uploaded package images are saved to `backend/data/uploads/` via [`storage.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/storage.py).
- Static File Mount: Backend automatically mounts `/uploads` as static directory in [`main.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/main.py).
- **Persistence Note:** Host environments with ephemeral filesystems (e.g. Heroku, default container instances) will lose stored images on restart unless persistent volume mounts are configured.

## 10. Frontend Deployment Step-by-Step

1. **Navigate to Frontend & Install Dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Set Build Environment Variable:**
   Create `frontend/.env`:
   ```yml
   VITE_API_URL=http://your-server-ip-or-domain:8000
   ```

3. **Build Production Static Bundle:**
   ```ps
   npm run build
   ```
   This generates an optimized single-page static bundle in `frontend/dist/`.

4. **Serve Static Assets:**
   Serve `frontend/dist/` using Nginx, Caddy, or FastAPI static file mount.

## 11. CORS Configuration
Ensure `CORS_ORIGINS` in `backend/.env` includes your deployed frontend domain or IP:
```yml
CORS_ORIGINS=http://localhost:5173,http://your-frontend-domain.com
```

## 12. Health Checks
The backend provides two built-in health check routes:
- **Liveness Check:** `GET http://127.0.0.1:8000/health` (Returns `{"status": "ok"}`)
- **Detailed Diagnostic Check:** `GET http://127.0.0.1:8000/health/detail` (Checks database connectivity, storage status, and active OCR mode).

## 13. Recommended Production Deployment Architectures (Cloud Options)

> [!NOTE]
> Cloud provider configuration files (such as `Dockerfile`, `docker-compose.yml`, `render.yaml`) are **not** present in the current repository. The deployment options below represent recommended architectural paths for cloud hosting.

### Recommended Option A: Linux VM (AWS EC2 / DigitalOcean Droplet)
- Install Nginx as reverse proxy on port 80/443.
- Proxy `/api` to Uvicorn running on `127.0.0.1:8000`.
- Serve `frontend/dist` directly from Nginx.
- Mount persistent block storage for `backend/data/`.

### Recommended Option B: PaaS (Render / Railway)
- **Backend Service:** Deploy `backend/` directory as Python web service. Run command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add persistent disk for `/data`.
- **Frontend Service:** Deploy `frontend/` directory as static site. Build command: `npm run build`, Publish directory: `dist`.

## 14. Logs & Troubleshooting

- **Server Log Inspection:** Uvicorn writes logs to stdout/stderr.
- **Database Locks (SQLite):** If encountering `sqlite3.OperationalError: database is locked`, ensure only one Uvicorn process writes to SQLite during migration runs.
- **OCR Initialization Error:** If PaddleOCR fails on Windows CPU, ensure `enable_mkldnn=False` is set (see [`paddle_provider.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/ocr/paddle_provider.py)).

## 15. Known Hosting Limitations
1. **SQLite Concurrency:** SQLite is suitable for single-station inspection prototypes. Enterprise multi-user concurrent write throughput requires migrating `DATABASE_URL` to PostgreSQL.
2. **Ephemeral File Storage:** Standard cloud container hosts delete local `/data/uploads` when containers restart unless persistent volume disk mounts are configured.
3. **Open Access Security:** The system lacks API authentication tokens; access to the host network port must be restricted using firewall rules or reverse proxy basic auth.

## 16. Cleanup & Reset Procedure
To clear all stored inspection records and reset to clean state:
```ps
# 1. Stop backend and frontend processes
# 2. Delete local SQLite database and upload directory contents
rm backend/data/metriguard.db
rm backend/data/uploads/*

# 3. Re-run migrations
cd backend
alembic upgrade head
```