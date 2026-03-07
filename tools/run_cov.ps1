\
# Runs Jarvis tests with coverage and writes htmlcov/
# Usage: powershell -ExecutionPolicy Bypass -File .\tools\run_cov.ps1
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
  . $venvActivate
}

python -m pytest -q --disable-warnings --maxfail=1 --cov=app --cov-report=term-missing --cov-report=html
