\
# Start Jarvis locally with Docker Postgres/Redis + DB-backed memory.
# Run from project root: .\start_local.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Import-DotEnv($path) {
  if (!(Test-Path $path)) { return }
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $parts = $line.Split("=",2)
    if ($parts.Length -ne 2) { return }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
  }
}

Write-Host "== Jarvis Local Start =="

Import-DotEnv ".\.env.local"

Write-Host "1) Starting Docker services (Postgres/Redis)..."
docker compose -f .\docker-compose.local.yml up -d

Write-Host "2) Activating venv..."
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
  & .\.venv\Scripts\Activate.ps1
} else {
  Write-Host "No .venv found. Creating one..."
  python -m venv .venv
  & .\.venv\Scripts\Activate.ps1
}

Write-Host "3) Installing requirements..."
pip install -r requirements.txt

Write-Host "4) Running DB migrations..."
alembic upgrade head

Write-Host "5) Starting API server on http://127.0.0.1:8010 ..."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
