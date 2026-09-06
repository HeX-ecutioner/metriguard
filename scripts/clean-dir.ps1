<#
.SYNOPSIS
    Safely removes disposable local development artifacts from the MetriGuard project.
.EXAMPLE
    .\scripts\clean-dir.ps1 -WhatIf
.EXAMPLE
    .\scripts\clean-dir.ps1
.EXAMPLE
    .\scripts\clean-dir.ps1 -Force
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param (
    [Parameter(Mandatory = $false, HelpMessage = "Skip interactive confirmation prompt.")]
    [Alias("f")]
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = if (Test-Path (Join-Path $PSScriptRoot "backend")) { $PSScriptRoot } else { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
if (-not (Test-Path (Join-Path $repoRoot "backend\app")) -or -not (Test-Path (Join-Path $repoRoot "frontend"))) {
    Write-Error "Safety check failed: Invalid repository root ($repoRoot)."
    exit 1
}

$isWhatIf = [bool]($PSBoundParameters.ContainsKey('WhatIf') -or $WhatIfPreference)
Write-Host "MetriGuard Workspace Cleanup" -ForegroundColor Cyan
Write-Host "Repository Root: $repoRoot`n" -ForegroundColor Gray

$targets = [System.Collections.Generic.List[PSCustomObject]]::new()
$skipped = [System.Collections.Generic.List[string]]::new()

function Add-Target([string]$Path, [string]$Type, [string]$Note = "") {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $full = (Resolve-Path -LiteralPath $Path).Path
    if (-not $full.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
        $full -match '\\\.git($|\\)' -or $full -match '\\alembic\\versions($|\\)' -or (Split-Path -Leaf $full) -in @(".git", ".gitkeep", ".env", ".env.example")) {
        $skipped.Add($full)
        return
    }
    if (-not ($targets | Where-Object { $_.FullPath -eq $full })) {
        $rel = $full.Substring($repoRoot.Length).TrimStart('\', '/')
        $targets.Add([PSCustomObject]@{ FullPath = $full; RelativePath = $rel; Type = $Type; Note = $Note })
    }
}

# Scan caches & bytecode across repository (pruning .git, .venv, node_modules)
function Scan-Dir([string]$dir) {
    foreach ($entry in (Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue)) {
        if ($entry.PSIsContainer) {
            if ($entry.Name -in @(".git", ".venv", "venv", "node_modules")) { continue }
            if ($entry.Name -in @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov")) {
                Add-Target $entry.FullName "Directory"
            } else {
                Scan-Dir $entry.FullName
            }
        } elseif ($entry.Extension -in @(".pyc", ".pyo", ".pyd") -or $entry.Name -match '^(\.coverage|\.coverage\..*|coverage\.xml|\.eslintcache)$') {
            Add-Target $entry.FullName "File"
        }
    }
}
Scan-Dir $repoRoot

# Specific frontend, storage, test & database artifacts
@( "frontend\dist", "frontend\dist-ssr", "frontend\coverage", "frontend\node_modules\.vite" ) | ForEach-Object { Add-Target (Join-Path $repoRoot $_) "Directory" }
@( "sample_package.jpg", "backend\sample_package.jpg" ) | ForEach-Object { Add-Target (Join-Path $repoRoot $_) "File" }

# Storage uploads & reports (preserving .gitkeep)
foreach ($sub in @("uploads", "reports")) {
    $storageDir = Join-Path $repoRoot "backend\storage\$sub"
    if (Test-Path $storageDir) {
        Get-ChildItem -LiteralPath $storageDir -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ne ".gitkeep" } |
            ForEach-Object {
                $itemType = if ($_.PSIsContainer) { "Directory" } else { "File" }
                Add-Target $_.FullName $itemType
            }
    }
}

# Local SQLite database files (preserving .gitkeep)
$dataDir = Join-Path $repoRoot "backend\data"
if (Test-Path $dataDir) {
    Get-ChildItem -LiteralPath $dataDir -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne ".gitkeep" -and $_.Extension -in @(".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm") } |
        ForEach-Object { Add-Target $_.FullName "File" "Resets local database (requires 'alembic upgrade head')" }
}
if ($targets.Count -eq 0) {
    Write-Host "[CLEAN] No disposable development artifacts found.`n" -ForegroundColor Green
    exit 0
}

Write-Host "Found $($targets.Count) disposable artifact(s):" -ForegroundColor Cyan
foreach ($item in $targets) {
    $tag = if ($item.Type -eq "Directory") { "[DIR ]" } else { "[FILE]" }
    $color = if ($item.Type -eq "Directory") { "Yellow" } else { "White" }
    Write-Host -NoNewline "  $tag " -ForegroundColor $color
    Write-Host "$($item.RelativePath)" -ForegroundColor Gray
    if ($item.Note) { Write-Host "         ! NOTE: $($item.Note)" -ForegroundColor Yellow }
}
Write-Host ""

if ($isWhatIf) {
    Write-Host "[WHATIF] Dry-run complete. No files were deleted.`n" -ForegroundColor Cyan
    exit 0
}

if (-not $Force) {
    $confirm = Read-Host "Delete these $($targets.Count) artifacts? [y/N]"
    if ($confirm -notmatch '^(y|yes)$') {
        Write-Host "[CANCELLED] Aborted by user.`n" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "`nDeleting artifacts..." -ForegroundColor Cyan
$deletedFiles = 0; $deletedDirs = 0
$errors = [System.Collections.Generic.List[string]]::new()

foreach ($target in $targets) {
    try {
        if (Test-Path -LiteralPath $target.FullPath) {
            Remove-Item -LiteralPath $target.FullPath -Recurse -Force -ErrorAction Stop
            if ($target.Type -eq "Directory") { $deletedDirs++ } else { $deletedFiles++ }
            Write-Host "  [DELETED] $($target.RelativePath)" -ForegroundColor Green
        }
    } catch {
        $errors.Add("Failed to delete $($target.RelativePath): $($_.Exception.Message)")
        Write-Host "  [FAILED]  $($target.RelativePath) ($($_.Exception.Message))" -ForegroundColor Red
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Cleanup Summary: $deletedFiles files, $deletedDirs directories deleted, $($errors.Count) errors." -ForegroundColor $(if ($errors.Count -gt 0) { "Yellow" } else { "Green" })
if ($targets | Where-Object { $_.RelativePath -match 'backend\\data\\.*\.db' }) {
    Write-Host "Local SQLite DB was removed. Run 'alembic upgrade head' or '.\start.ps1' to reinitialize." -ForegroundColor Cyan
}
Write-Host "============================================================`n" -ForegroundColor Cyan

if ($errors.Count -gt 0) { exit 1 } else { exit 0 }
