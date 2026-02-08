<#
Jarvis starter - single command (Windows PowerShell)

Run from repo root:
  .\jarvis.ps1

If PowerShell blocks scripts:
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
#>

[CmdletBinding()]
param(
  [string]$EnvFile = ".\.env.local",
  [string]$ApiHost = "",
  [int]$ApiPort = 0,
  [switch]$Install,
  [switch]$NoDocker,
  [switch]$NoReload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Info([string]$m){ Write-Host $m }
function Warn([string]$m){ Write-Host ("WARN: " + $m) -ForegroundColor Yellow }
function Ok([string]$m){ Write-Host ("OK:   " + $m) -ForegroundColor Green }
function Fail([string]$m){ Write-Host ("ERR:  " + $m) -ForegroundColor Red }

function Ensure-RepoRoot {
  if (!(Test-Path ".\app") -or !(Test-Path ".\requirements.txt")) {
    throw "Run this script from the repo root (folder containing .\app and requirements.txt)."
  }
}

function Import-DotEnv([string]$path){
  if (!(Test-Path $path)) { return $false }
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $parts = $line.Split("=",2)
    if ($parts.Length -ne 2) { return }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
      $value = $value.Substring(1, $value.Length-2)
    }
    [System.Environment]::SetEnvironmentVariable($name,$value,"Process")
  }
  return $true
}

function Ensure-GitWorkBranch {
  if (!(Test-Path ".git")) { Warn "No .git folder - skipping branch switch."; return }
  $git = Get-Command git -ErrorAction SilentlyContinue
  if (-not $git) { Warn "git not found - skipping branch switch."; return }
  try {
    $branch = (& git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    if ($branch -ne "work") {
      Warn ("Switching git branch: " + $branch + " -> work")
      & git switch work | Out-Host
    } else {
      Ok "git branch: work"
    }
  } catch {
    Warn ("Could not switch branch: " + $_.Exception.Message)
  }
}

function Ensure-Venv {
  $venvDir = ".\.venv"
  $venvPy  = Join-Path $venvDir "Scripts\python.exe"

  if (!(Test-Path $venvPy)) {
    Info "Creating venv in .\.venv ..."
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
      try {
        & py -3.11 -m venv $venvDir | Out-Host
      } catch {
        & py -3 -m venv $venvDir | Out-Host
      }
    } else {
      $python = Get-Command python -ErrorAction SilentlyContinue
      if (-not $python) { throw "Python not found. Install Python and ensure 'py' or 'python' works in PowerShell." }
      & python -m venv $venvDir | Out-Host
    }
  }

  $activate = Join-Path $venvDir "Scripts\Activate.ps1"
  if (Test-Path $activate) { . $activate }

  return $venvPy
}

function Install-Dependencies([string]$venvPy){
  if (-not $Install) { return }
  Info "Installing requirements (forced) ..."
  & $venvPy -m pip install --upgrade pip setuptools wheel | Out-Host
  & $venvPy -m pip install -r requirements.txt | Out-Host
  try { & $venvPy -m alembic upgrade head | Out-Host } catch { Warn ("alembic upgrade failed (may be OK): " + $_.Exception.Message) }
}

function Start-DockerIfConfigured {
  if ($NoDocker) { return }

  $backend = ("" + $env:MEMORY_BACKEND).Trim().ToLower()
  $dbUrl   = ("" + $env:DATABASE_URL).Trim().ToLower()
  $wantsDb = ($backend -eq "db") -or ($dbUrl.StartsWith("postgres"))

  if (-not $wantsDb) { return }

  if (!(Test-Path ".\docker-compose.local.yml")) {
    Warn "db mode detected but docker-compose.local.yml not found - skipping Docker."
    return
  }

  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if (-not $docker) {
    Warn "docker not found - skipping Docker."
    return
  }

  try {
    Info "Starting Docker services (docker compose up -d) ..."
    & docker compose -f docker-compose.local.yml up -d | Out-Host
  } catch {
    Warn ("docker compose failed: " + $_.Exception.Message)
  }
}

function Ensure-EnvDefaults {
  if ([string]::IsNullOrWhiteSpace($env:API_HOST)) { $env:API_HOST = "127.0.0.1" }
  if ([string]::IsNullOrWhiteSpace($env:API_PORT)) { $env:API_PORT = "8010" }

  if ($ApiHost -ne "") { $env:API_HOST = $ApiHost }
  if ($ApiPort -gt 0)  { $env:API_PORT = "$ApiPort" }

  if ([string]::IsNullOrWhiteSpace($env:API_URL)) {
    $env:API_URL = "http://$($env:API_HOST):$($env:API_PORT)/v1/chat"
  }
  if ([string]::IsNullOrWhiteSpace($env:API_TOKEN)) {
    $env:API_TOKEN = "dev-token"
  }
  if ([string]::IsNullOrWhiteSpace($env:JARVIS_MODE)) {
    $env:JARVIS_MODE = "b2c"
  }
}

function Start-CLI {
  $cliScript = ".\start_cli.ps1"
  if (!(Test-Path $cliScript)) {
    Warn "start_cli.ps1 not found - skipping CLI."
    return
  }

  Info "Starting CLI in a new PowerShell window ..."
  $args = "-NoExit -ExecutionPolicy Bypass -File `"$cliScript`""
  Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $PSScriptRoot | Out-Null
}

function Start-API([string]$venvPy) {
  # If repo provides start_server.ps1 and user did not request -NoReload, we can use it.
  $serverScript = ".\start_server.ps1"
  if ((Test-Path $serverScript) -and (-not $NoReload)) {
    Info "Starting API via start_server.ps1 ..."
    & $serverScript
    return
  }

  Info "Starting API via uvicorn ..."
  $uvArgs = @("app.main:app","--host",$env:API_HOST,"--port",$env:API_PORT)
  if (-not $NoReload) { $uvArgs += "--reload" }
  & $venvPy -m uvicorn @uvArgs
}

# ---- MAIN ----
Ensure-RepoRoot
Ensure-GitWorkBranch

if (-not (Import-DotEnv $EnvFile)) {
  if (Test-Path ".\.env") { Import-DotEnv ".\.env" | Out-Null }
}

Ensure-EnvDefaults
Start-DockerIfConfigured

$venvPy = Ensure-Venv
Install-Dependencies $venvPy

Ok "Jarvis config:"
Info ("  API docs: http://{0}:{1}/docs" -f $env:API_HOST, $env:API_PORT)
Info ("  API URL : {0}" -f $env:API_URL)
Info ("  MODE    : {0}" -f $env:JARVIS_MODE)

Start-CLI
Start-API $venvPy
