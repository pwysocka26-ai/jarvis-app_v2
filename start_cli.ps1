# start_cli.ps1
# Starts Jarvis CLI (talks to Jarvis API). Requires server running (or start it with jarvis.ps1).
# Run:
#   .\start_cli.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

if (!(Test-Path ".\.venv\Scripts\Activate.ps1")) {
  throw "Brak .\.venv\Scripts\Activate.ps1. Uruchom najpierw .\jarvis.ps1 (on utworzy venv automatycznie)."
}

. .\.venv\Scripts\Activate.ps1

# Token: accept both names, keep in sync
if ($env:JARVIS_API_TOKEN -and -not $env:API_TOKEN) { $env:API_TOKEN = $env:JARVIS_API_TOKEN }
if ($env:API_TOKEN -and -not $env:JARVIS_API_TOKEN) { $env:JARVIS_API_TOKEN = $env:API_TOKEN }
if (-not $env:API_TOKEN -and -not $env:JARVIS_API_TOKEN) {
  $env:API_TOKEN = "dev-token"
  $env:JARVIS_API_TOKEN = "dev-token"
}

# API_URL for CLI
if (-not $env:API_URL -or $env:API_URL.Trim() -eq "") {
  $h = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
  $p = if ($env:API_PORT) { $env:API_PORT } else { "8010" }
  $env:API_URL = "http://$h`:$p/v1/chat"
}

# Default CLI mode
if (-not $env:JARVIS_MODE -or $env:JARVIS_MODE.Trim() -eq "") {
  $env:JARVIS_MODE = "b2c"
}

python tools\chat_cli.py
