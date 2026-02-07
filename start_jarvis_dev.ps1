# start_jarvis_dev.ps1
$ErrorActionPreference = "Stop"

Write-Host "== Jarvis DEV starter =="

# 1) Wejście do katalogu skryptu
Set-Location -Path $PSScriptRoot

# 2) Wybór Pythona 3.11 (masz go na screenach jako py -3.11)
$PY = "py -3.11"

# 3) Tworzenie venv jeśli brak
if (!(Test-Path ".\.venv")) {
    Write-Host ">> Creating venv (.venv) with Python 3.11..."
    iex "$PY -m venv .venv"
}

# 4) Python i pip z venv
$VENV_PY = ".\.venv\Scripts\python.exe"

Write-Host ">> Upgrading pip/setuptools/wheel..."
& $VENV_PY -m pip install --upgrade pip setuptools wheel

Write-Host ">> Installing requirements..."
& $VENV_PY -m pip install -r requirements.txt

# 5) DEV auth (żeby nie wymagał ENTRA_AUDIENCE)
$env:AUTH_MODE = "dev"
$env:ENTRA_ENABLED = "false"
$env:DEV_API_KEY = "demo-token"

Write-Host ">> Running migrations (alembic upgrade head)..."
& $VENV_PY -m alembic upgrade head

# 6) Start API
Write-Host ">> Starting Jarvis API on http://127.0.0.1:8010 ..."
Write-Host "   (Stop: CTRL+C in this window)"
& $VENV_PY -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
