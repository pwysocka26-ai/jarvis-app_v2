# start_server.ps1
# Starts Jarvis API (uvicorn). Can be run standalone:
#   .\start_server.ps1
# or via jarvis.ps1 (recommended)

[CmdletBinding()]
param(
  [string]$ApiHost = "",
  [int]$ApiPort = 0,
  [switch]$NoReload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

if (!(Test-Path ".\.venv\Scripts\Activate.ps1")) {
  throw "Brak .\.venv\Scripts\Activate.ps1. Uruchom najpierw .\jarvis.ps1 (on utworzy venv automatycznie)."
}

. .\.venv\Scripts\Activate.ps1

if (-not $ApiHost -or $ApiHost.Trim() -eq "") {
  if ($env:API_HOST) { $ApiHost = $env:API_HOST } else { $ApiHost = "127.0.0.1" }
}
if ($ApiPort -le 0) {
  if ($env:API_PORT) { $ApiPort = [int]$env:API_PORT } else { $ApiPort = 8010 }
}

$uvArgs = @("app.main:app","--host",$ApiHost,"--port",$ApiPort)
if (-not $NoReload) { $uvArgs += "--reload" }

python -m uvicorn @uvArgs
