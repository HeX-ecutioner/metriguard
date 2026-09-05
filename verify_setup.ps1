# MetriGuard - Native Windows Environment Verification Script
# Validates the complete Docker-free setup

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MetriGuard Native Windows Setup Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = $PSScriptRoot
$allPassed = $true

function Report-Check {
    param (
        [string]$Name,
        [bool]$Success,
        [string]$Details = ""
    )
    if ($Success) {
        Write-Host " [PASS] $Name" -ForegroundColor Green
        if ($Details) { Write-Host "        $Details" -ForegroundColor Gray }
    } else {
        Write-Host " [FAIL] $Name" -ForegroundColor Red
        if ($Details) { Write-Host "        $Details" -ForegroundColor Yellow }
        $script:allPassed = $false
    }
}

# 1. Check Python
try {
    $py = & python --version 2>&1
    $pyOk = $py -match "Python 3\.(1[1-9]|[2-9]\d)"
    Report-Check "System Python 3.11+" $pyOk "$py"
} catch {
    Report-Check "System Python 3.11+" $false "Python is not found on PATH"
}

# 2. Check Node & npm
try {
    $node = & node --version 2>&1
    $npm = & npm --version 2>&1
    Report-Check "Node.js & npm" $true "Node: $node, npm: v$npm"
} catch {
    Report-Check "Node.js & npm" $false "Node.js / npm not found on PATH"
}

# 3. Check Backend Virtual Environment
$venvPath = Join-Path $rootDir "backend\.venv\Scripts\python.exe"
$venvExists = Test-Path $venvPath
Report-Check "Python Virtual Environment (backend/.venv)" $venvExists "Path: $venvPath"

# 4. Check Backend Directory Layout
$dataPath = Join-Path $rootDir "backend\data"
$storagePath = Join-Path $rootDir "backend\storage"
Report-Check "Local Data Directory (backend/data)" (Test-Path $dataPath) "$dataPath"
Report-Check "Local Storage Directory (backend/storage)" (Test-Path $storagePath) "$storagePath"

# 5. Check Backend Migrations & Database Initialization
if ($venvExists) {
    try {
        $alembicExe = Join-Path $rootDir "backend\.venv\Scripts\alembic.exe"
        Push-Location (Join-Path $rootDir "backend")
        $migOut = & $alembicExe upgrade head 2>&1
        Pop-Location
        $dbFile = Join-Path $dataPath "metriguard.db"
        $dbExists = Test-Path $dbFile
        Report-Check "Alembic Migrations & SQLite DB File" $dbExists "Database: $dbFile"
    } catch {
        Report-Check "Alembic Migrations & SQLite DB File" $false "Migration error: $_"
    }
} else {
    Report-Check "Alembic Migrations & SQLite DB File" $false "Skipped: .venv not found"
}

# 6. Run Backend Tests
if ($venvExists) {
    try {
        Push-Location (Join-Path $rootDir "backend")
        $pytestOut = & $venvPath -m pytest tests -q 2>&1
        $pytestPassed = $LASTEXITCODE -eq 0
        Pop-Location
        Report-Check "Backend Unit Tests (pytest)" $pytestPassed "$pytestOut"
    } catch {
        Report-Check "Backend Unit Tests (pytest)" $false "Pytest failed: $_"
    }
} else {
    Report-Check "Backend Unit Tests (pytest)" $false "Skipped: .venv not found"
}

# 7. Check Frontend Dependencies & Typecheck
$frontendDir = Join-Path $rootDir "frontend"
$nodeModules = Join-Path $frontendDir "node_modules"
Report-Check "Frontend Dependencies (node_modules)" (Test-Path $nodeModules)

if (Test-Path $nodeModules) {
    try {
        Push-Location $frontendDir
        $buildOut = & npm run build 2>&1
        $buildPassed = $LASTEXITCODE -eq 0
        Pop-Location
        Report-Check "Frontend TypeScript Build (npm run build)" $buildPassed
    } catch {
        Report-Check "Frontend TypeScript Build (npm run build)" $false "Build error: $_"
    }
} else {
    Report-Check "Frontend TypeScript Build (npm run build)" $false "Skipped: node_modules missing"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "  SUCCESS: Native Windows Environment Verified 100%!" -ForegroundColor Green
    Write-Host "  Ready to launch with: .\start.ps1 or start.bat" -ForegroundColor Green
} else {
    Write-Host "  FAILED: One or more checks failed. Please see above for details." -ForegroundColor Red
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
