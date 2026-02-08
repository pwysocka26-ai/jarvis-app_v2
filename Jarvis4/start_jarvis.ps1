param(
  [int]$Port = 8010,
  [string]$Token = "dev-token",
  [string]$OllamaBaseUrl = "http://127.0.0.1:11434"
)

# --- Git safety: always work on 'work' branch ---
try {
  git checkout work 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    git checkout -b work | Out-Null
  }
} catch {
  # If git is not available, continue (Jarvis can still run)
}
$ErrorActionPreference = "Stop"

function Assert-File($p) { if (-not (Test-Path $p)) { throw "Nie znaleziono pliku: $p. Uruchom w katalogu Jarvis4." } }

Assert-File ".\.venv\Scripts\activate.ps1"

. .\.venv\Scripts\activate.ps1

$env:API_TOKEN = $Token
$env:JARVIS_API_TOKEN = $Token
$env:API_URL = "http://127.0.0.1:$Port/v1/chat"
$env:OLLAMA_BASE_URL = $OllamaBaseUrl
$env:OLLAMA_MODEL = "llama3"

Write-Host "✅ ENV ustawione:"
Write-Host "  API_URL=$env:API_URL"
Write-Host "  OLLAMA_BASE_URL=$env:OLLAMA_BASE_URL"
Write-Host "  OLLAMA_MODEL=$env:OLLAMA_MODEL"
Write-Host ""

$serverCmd = "cd `"$PWD`"; . .\.venv\Scripts\activate.ps1; `$env:API_TOKEN=`"$Token`"; `$env:JARVIS_API_TOKEN=`"$Token`"; `$env:API_URL=`"http://127.0.0.1:$Port/v1/chat`"; `$env:OLLAMA_BASE_URL=`"$OllamaBaseUrl`"; `$env:OLLAMA_MODEL=`"llama3`"; python -m uvicorn app.main:app --host 127.0.0.1 --port $Port"
Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-Command",$serverCmd | Out-Null

Start-Sleep -Seconds 2

$cliCmd = "cd `"$PWD`"; . .\.venv\Scripts\activate.ps1; `$env:API_TOKEN=`"$Token`"; `$env:JARVIS_API_TOKEN=`"$Token`"; `$env:API_URL=`"http://127.0.0.1:$Port/v1/chat`"; python tools\chat_cli.py"
Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-Command",$cliCmd | Out-Null

Write-Host "🚀 Uruchomiono dwa okna: SERWER + CLI."
Write-Host "W CLI używaj: /mode b2c lub /mode pro"
