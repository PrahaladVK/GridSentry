$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating backend virtual environment..."
    python -m venv (Join-Path $backend ".venv")
}

Write-Host "Installing backend dependencies..."
& $venvPython -m pip install -q -r (Join-Path $backend "requirements.txt")

$dbPath = Join-Path $backend "artifacts\gridsentry.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "Seeding database and training models (first run, a few minutes)..."
    Push-Location $backend
    & $venvPython seed.py
    Pop-Location
}

$nodeModules = Join-Path $frontend "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $frontend
    npm install
    Pop-Location
}

Write-Host "Starting backend on http://127.0.0.1:8000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000"

Write-Host "Starting frontend on http://localhost:5173 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontend'; npm run dev"

Start-Sleep -Seconds 4
Start-Process "http://localhost:5173"

Write-Host "GridSentry is starting in two new windows. Close them to stop it."
