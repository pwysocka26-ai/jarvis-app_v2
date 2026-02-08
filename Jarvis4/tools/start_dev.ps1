$ErrorActionPreference = 'Stop'

# PowerShell:
#   powershell -ExecutionPolicy Bypass -File tools\start_dev.ps1

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..

if (!(Test-Path '.venv')) { py -3.11 -m venv .venv }
. .\.venv\Scripts\Activate.ps1

$env:AUTH_MODE='dev'
$env:ENTRA_ENABLED='false'
$env:DEV_API_KEY='demo-token'

python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --port 8010 --reload
