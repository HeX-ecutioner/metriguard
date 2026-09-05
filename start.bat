@echo off
title MetriGuard Launcher
set "ROOT_DIR=%~dp0"

echo ============================================================
echo   MetriGuard - Local Development Mode
echo ============================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 goto :nopypy

where npm >nul 2>nul
if %ERRORLEVEL% neq 0 goto :nonpm

echo [MetriGuard] Cleaning up any lingering processes on ports 8000 and 5173...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = @(8000, 5173); foreach ($p in $ports) { Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"

echo [MetriGuard] Setting up Backend...
cd /d "%ROOT_DIR%backend"
if exist ".venv" goto :backend_ready

echo [MetriGuard] Creating Python virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat
echo [MetriGuard] Installing backend dependencies...
pip install -r requirements.txt
echo [MetriGuard] Applying database migrations (SQLite)...
call alembic upgrade head
goto :frontend_setup

:backend_ready
call .venv\Scripts\activate.bat
echo [MetriGuard] Checking database migrations (SQLite)...
call alembic upgrade head

:frontend_setup
echo [MetriGuard] Setting up Frontend...
cd /d "%ROOT_DIR%frontend"
if exist "node_modules" goto :run_apps

echo [MetriGuard] Installing frontend dependencies...
call npm install

:run_apps
echo.
echo ============================================================
echo  Starting MetriGuard Services
echo  - Frontend UI:  http://localhost:5173
echo  - Backend API:  http://localhost:8000
echo  - Swagger Docs: http://localhost:8000/docs
echo ============================================================
echo.

echo [MetriGuard] Starting Backend API in separate window (Port 8000)...
start "MetriGuard Backend API" cmd /k "cd /d ""%ROOT_DIR%backend"" && call .venv\Scripts\activate.bat && set ""USE_MOCK_EXTRACTOR=false"" && python -m uvicorn app.main:app --reload --port 8000"

echo [MetriGuard] Starting Frontend UI (Port 5173)...
cd /d "%ROOT_DIR%frontend"
call npm run dev

goto :eof

:nopypy
echo [ERROR] Python is not installed or not added to PATH.
pause
exit /b 1

:nonpm
echo [ERROR] Node.js / npm is not installed or not added to PATH.
pause
exit /b 1
