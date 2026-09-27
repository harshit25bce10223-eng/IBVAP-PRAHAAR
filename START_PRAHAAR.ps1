# PRAHAAR — Universal Startup Script (PowerShell)
# Double-click to run, OR: Right-click → "Run with PowerShell"

$Host.UI.RawUI.WindowTitle = "PRAHAAR — Universal Startup"

$banner = @"

  ╔══════════════════════════════════════════════════════╗
  ║   प्रहार  |  AI-Powered Intelligent Border Surveillance  ║
  ║   SSB Command & Control Platform                     ║
  ╚══════════════════════════════════════════════════════╝

"@

Write-Host $banner -ForegroundColor Cyan

$BACKEND  = "C:\SIH\ibvap-backend"
$FRONTEND = "C:\SIH\ibvap-frontend"

# ─── Checks ──────────────────────────────────────────────────────
function Check-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

if (-not (Check-Command "python")) {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+ and add it to PATH." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Check-Command "node")) {
    Write-Host "[ERROR] Node.js not found. Please install Node.js 18+ and add it to PATH." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ─── Backend venv setup ──────────────────────────────────────────
if (-not (Test-Path "$BACKEND\venv")) {
    Write-Host "[1/4] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv "$BACKEND\venv"
    Write-Host "[2/4] Installing backend dependencies (pip)..." -ForegroundColor Yellow
    & "$BACKEND\venv\Scripts\pip" install -r "$BACKEND\requirements.txt" --quiet
    Write-Host "      Done." -ForegroundColor Green
} else {
    Write-Host "[1/4] venv already exists — skipped." -ForegroundColor DarkGray
    Write-Host "[2/4] pip install skipped." -ForegroundColor DarkGray
}

# ─── Frontend node_modules setup ─────────────────────────────────
if (-not (Test-Path "$FRONTEND\node_modules")) {
    Write-Host "[3/4] Installing frontend dependencies (npm)..." -ForegroundColor Yellow
    Push-Location $FRONTEND
    npm install --silent
    Pop-Location
    Write-Host "      Done." -ForegroundColor Green
} else {
    Write-Host "[3/4] node_modules already exists — skipped." -ForegroundColor DarkGray
}

Write-Host "[4/4] Launching services..." -ForegroundColor Yellow
Write-Host ""

# ─── Start Backend ────────────────────────────────────────────────
$backendCmd = @"
cd /d $BACKEND
call venv\Scripts\activate
echo.
echo  [BACKEND] FastAPI running on http://127.0.0.1:8000
echo  [BACKEND] Swagger docs: http://127.0.0.1:8000/docs
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"@

Start-Process cmd -ArgumentList "/k", $backendCmd `
    -WindowStyle Normal `
    -WorkingDirectory $BACKEND

Start-Sleep -Seconds 2

# ─── Start Frontend ───────────────────────────────────────────────
$frontendCmd = @"
cd /d $FRONTEND
echo.
echo  [FRONTEND] Vite dev server on http://127.0.0.1:5173
echo.
npm run dev
"@

Start-Process cmd -ArgumentList "/k", $frontendCmd `
    -WindowStyle Normal `
    -WorkingDirectory $FRONTEND

Start-Sleep -Seconds 3

# ─── Open browser ────────────────────────────────────────────────
Start-Process "http://127.0.0.1:5173"

# ─── Summary ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║   ALL SERVICES STARTED!                  ║" -ForegroundColor Green
Write-Host "  ║                                          ║" -ForegroundColor Green
Write-Host "  ║   Frontend  →  http://127.0.0.1:5173    ║" -ForegroundColor Green
Write-Host "  ║   Backend   →  http://127.0.0.1:8000    ║" -ForegroundColor Green
Write-Host "  ║   API Docs  →  http://127.0.0.1:8000/docs ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Close the individual CMD windows to stop each service." -ForegroundColor DarkYellow
Write-Host ""
Read-Host "Press Enter to close this launcher"
