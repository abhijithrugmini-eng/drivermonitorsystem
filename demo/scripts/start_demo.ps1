<#
.SYNOPSIS
    One-click start for the Driver Monitor POC demo: backend + UI + seeded sample data.

.DESCRIPTION
    Sets up (if needed) and starts dms-backend and dms-ui, waits for the backend
    to come up, then runs dms-backend/scripts/seed_demo.py to populate the
    dashboard with sample violations. Does NOT start dms-edge (that needs a real
    video file / camera and is run separately - see demo/DEMO_GUIDE.md).

    Safe to re-run: reuses existing virtualenvs/node_modules instead of recreating them.
#>

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "dms-backend"
$UiDir      = Join-Path $RepoRoot "dms-ui"
$PidFile    = Join-Path $PSScriptRoot ".demo_pids.json"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
# 1. Prerequisite checks
# ---------------------------------------------------------------------------
Write-Step "Checking prerequisites"

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $pyLauncher) {
    Write-Error "Python launcher 'py' not found. Install Python 3.11+ from python.org and re-run."
    exit 1
}
$pyVersionOutput = & py -3.11 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 3.11 not found via 'py -3.11'. Install Python 3.11+ and re-run."
    exit 1
}
Write-Ok "$pyVersionOutput"

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Error "Node.js not found. Install Node 18+ (20+ recommended) from nodejs.org and re-run."
    exit 1
}
Write-Ok "Node $(node --version)"

# ---------------------------------------------------------------------------
# 2. Backend: venv + install + start
# ---------------------------------------------------------------------------
Write-Step "Setting up dms-backend"

$BackendVenv = Join-Path $BackendDir ".venv"
if (-not (Test-Path $BackendVenv)) {
    Write-Warn "Creating virtual environment (first run only)..."
    & py -3.11 -m venv $BackendVenv
}

$BackendPip = Join-Path $BackendVenv "Scripts\pip.exe"
$BackendPy  = Join-Path $BackendVenv "Scripts\python.exe"

Write-Warn "Installing/verifying dependencies..."
& $BackendPip install -q -r (Join-Path $BackendDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed for dms-backend. See demo/DEMO_GUIDE.md Troubleshooting (mediapipe/libexpat note)."
    exit 1
}
Write-Ok "Backend dependencies ready"

Write-Step "Starting dms-backend on http://localhost:8000"
$BackendProc = Start-Process -FilePath $BackendPy `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $BackendDir `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $PSScriptRoot "backend.log") `
    -RedirectStandardError (Join-Path $PSScriptRoot "backend.err.log")
Write-Ok "Backend process started (PID $($BackendProc.Id)), logs at demo/backend.log"

# ---------------------------------------------------------------------------
# 3. UI: npm install + start
# ---------------------------------------------------------------------------
Write-Step "Setting up dms-ui"

$UiNodeModules = Join-Path $UiDir "node_modules"
if (-not (Test-Path $UiNodeModules)) {
    Write-Warn "Running npm install (first run only)..."
    Push-Location $UiDir
    npm install
    Pop-Location
    if ($LASTEXITCODE -ne 0) {
        Write-Error "npm install failed for dms-ui."
        exit 1
    }
}
Write-Ok "UI dependencies ready"

Write-Step "Starting dms-ui on http://localhost:5173"
$UiProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $UiDir `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $PSScriptRoot "ui.log") `
    -RedirectStandardError (Join-Path $PSScriptRoot "ui.err.log")
Write-Ok "UI process started (PID $($UiProc.Id)), logs at demo/ui.log"

# Save PIDs so stop_demo.ps1 can find them later
@{ backend = $BackendProc.Id; ui = $UiProc.Id } | ConvertTo-Json | Set-Content -Path $PidFile -Encoding utf8

# ---------------------------------------------------------------------------
# 4. Wait for backend to respond
# ---------------------------------------------------------------------------
Write-Step "Waiting for backend to become ready"
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) {
    Write-Error "Backend did not become ready within 30s. Check demo/backend.err.log for details."
    exit 1
}
Write-Ok "Backend is up"

# ---------------------------------------------------------------------------
# 5. Seed sample data
# ---------------------------------------------------------------------------
Write-Step "Seeding sample violations (drowsiness, phone use, distraction, continuous drive)"
Push-Location $BackendDir
& $BackendPy "scripts\seed_demo.py"
Pop-Location
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Seed script exited with an error - the backend/UI are still running, check demo/backend.err.log."
} else {
    Write-Ok "Sample data injected"
}

# ---------------------------------------------------------------------------
# 6. Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Dashboard:  http://localhost:5173" -ForegroundColor Green
Write-Host " Backend API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host " To stop everything:  .\demo\stop_demo.ps1" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
