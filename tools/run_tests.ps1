# Run all tests from project root (prevents pytest from scanning user profile folders).
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here

Set-Location $root

if (Test-Path .\.venv\Scripts\Activate.ps1) {
  . .\.venv\Scripts\Activate.ps1
}

python -m pytest -q --disable-warnings --maxfail=1 --cov=app --cov-report=term-missing --cov-report=html
