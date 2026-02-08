# One-time installer for Windows.
# Creates .venv and installs Python deps.

$ErrorActionPreference = 'Stop'

python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "OK. Next: copy .env.example to .env and run .\\start_server.ps1" -ForegroundColor Green
