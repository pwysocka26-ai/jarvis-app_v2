param(
  [string]$ProjectRoot = ""
)

function Info($msg) { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Resolve project root
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $ProjectRoot = (Get-Location).Path
}
if (-not (Test-Path $ProjectRoot)) {
  Err "ProjectRoot not found: $ProjectRoot"
  exit 2
}

Info "Project root: $ProjectRoot"

# Find python
$py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Warn "No .venv python at $py"
  $py = $null
  foreach ($cand in @("py -3", "python", "python3")) {
    try {
      & $cand --version *> $null
      $py = $cand
      break
    } catch {}
  }
  if (-not $py) {
    Err "Could not find Python. Activate venv or install Python."
    exit 3
  }
} else {
  Info "Python cmd: $py"
}

# Ensure pip
Info "Checking pip..."
try {
  & $py -m pip --version *> $null
} catch {
  Warn "pip missing, trying ensurepip..."
  try {
    & $py -m ensurepip --upgrade
  } catch {
    Err "ensurepip failed. Cannot continue."
    exit 4
  }
}

# Install pytest
Info "Installing pytest..."
try {
  & $py -m pip install -q --disable-pip-version-check pytest
} catch {
  Err "Failed to install pytest."
  exit 5
}

# Run only sanity tests to avoid collecting archived tests
Info "Running tests (tests_sanity)..."
$code = 0
try {
  & $py -m pytest -q "tests_sanity" 
  $code = $LASTEXITCODE
} catch {
  $code = 1
}

if ($code -eq 0) {
  Info "OK. Tests passed."
} else {
  Err "Tests failed. ExitCode=$code"
}

exit $code
