# MetriGuard - Native Windows PowerShell Launcher
# 100% Docker-Free Local Startup Script

$ErrorActionPreference = "Stop"
$rootDir = $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MetriGuard - Native Windows Startup (Docker-Free)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Verify Python
try {
    $pyVer = & python --version 2>&1
    Write-Host "[MetriGuard] Found Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Error "[ERROR] Python is not installed or not available on PATH."
    exit 1
}

# Verify npm
try {
    $npmVer = & npm --version 2>&1
    Write-Host "[MetriGuard] Found npm: v$npmVer" -ForegroundColor Green
} catch {
    Write-Error "[ERROR] Node.js / npm is not installed or not available on PATH."
    exit 1
}

# Free up ports 8000 and 5173 if currently occupied
Write-Host "[MetriGuard] Checking for lingering processes on ports 8000 and 5173..." -ForegroundColor Yellow
$ports = @(8000, 5173)
foreach ($port in $ports) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Host "  Terminated process $($_.OwningProcess) on port $port." -ForegroundColor Gray
        } catch {}
    }
}

# Backend Setup
$backendDir = Join-Path $rootDir "backend"
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[MetriGuard] Creating Python virtual environment at backend\.venv..." -ForegroundColor Cyan
    & python -m venv $venvDir
    Write-Host "[MetriGuard] Installing backend dependencies..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt")
    $ocrReq = Join-Path $backendDir "requirements-ocr.txt"
    if (Test-Path $ocrReq) {
        Write-Host "[MetriGuard] Installing OCR dependencies (PaddleOCR)..." -ForegroundColor Cyan
        & $venvPython -m pip install -r $ocrReq
    }
} else {
    Write-Host "[MetriGuard] Backend virtual environment verified." -ForegroundColor Green
}

# Run database migrations
Write-Host "[MetriGuard] Applying Alembic database migrations..." -ForegroundColor Cyan
Push-Location $backendDir
try {
    $alembicExe = Join-Path $venvDir "Scripts\alembic.exe"
    & $alembicExe upgrade head
    Write-Host "[MetriGuard] Database schema is up to date (SQLite)." -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Alembic migration check encountered: $_" -ForegroundColor Yellow
} finally {
    Pop-Location
}

# Frontend Setup
$frontendDir = Join-Path $rootDir "frontend"
$nodeModules = Join-Path $frontendDir "node_modules"

if (-not (Test-Path $nodeModules)) {
    Write-Host "[MetriGuard] Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $frontendDir
    & npm install
    Pop-Location
} else {
    Write-Host "[MetriGuard] Frontend dependencies verified." -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Starting MetriGuard Native Services" -ForegroundColor Green
Write-Host "  - Frontend UI:   http://localhost:5173" -ForegroundColor Green
Write-Host "  - Backend API:   http://localhost:8000" -ForegroundColor Green
Write-Host "  - Health Check:  http://localhost:8000/health" -ForegroundColor Green
Write-Host "  - Swagger Docs:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

# Start Backend in a dedicated window
Write-Host "[MetriGuard] Launching Backend API in background window..." -ForegroundColor Cyan
$backendCommand = "cd '$backendDir'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $backendCommand

# Start Frontend in current terminal
Write-Host "[MetriGuard] Starting Frontend Dev Server..." -ForegroundColor Cyan
Set-Location $frontendDir
& npm run dev
