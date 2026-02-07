\
param(
  [string]$ProjectRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

function Backup-File($path) {
  if (Test-Path $path) {
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $bak = "$path.bak_$ts"
    Copy-Item $path $bak -Force
    Write-Host "Backup: $bak"
  } else {
    throw "Nie znaleziono pliku: $path"
  }
}

$corePath = Join-Path $ProjectRoot "app\orchestrator\core.py"
$mainPath = Join-Path $ProjectRoot "app\main.py"

Backup-File $corePath
Backup-File $mainPath

$core = Get-Content $corePath -Raw -Encoding UTF8

if ($core -match "async\s+def\s+handle_chat\s*\(" -or $core -match "def\s+handle_chat\s*\(") {
  Write-Host "OK: handle_chat już istnieje w core.py (nic nie dopisuję)."
} else {
  $block = @"

# --- AUTO-FIX: handle_chat (memory-safe) ---
from app.orchestrator.llm import get_llm_reply
from app.orchestrator.memory import format_memory_context

async def handle_chat(message: str, session_id: str | None = None) -> dict:
    \"\"\"
    Główna funkcja obsługi czatu – punkt wejścia dla API (/v1/chat)
    \"\"\"
    memory_context = ""
    if session_id:
        try:
            memory_context = format_memory_context(session_id)
        except Exception:
            memory_context = ""

    prompt = message
    if memory_context:
        prompt = f"{memory_context}\n\nUser: {message}"

    reply = await get_llm_reply(prompt)

    return {"reply": reply}
# --- END AUTO-FIX ---

"@

  Add-Content -Path $corePath -Value $block -Encoding UTF8
  Write-Host "Dopisano handle_chat do core.py"
}

$main = Get-Content $mainPath -Raw -Encoding UTF8

# Wymuś poprawny import w main.py
$desired = "from app.orchestrator.core import handle_chat"

if ($main -match "from\s+app\.orchestrator\.core\s+import\s+handle_chat") {
  Write-Host "OK: main.py już importuje handle_chat."
} else {
  # Usuń potencjalne złe importy handle_chat
  $main2 = [regex]::Replace($main, "^from\s+app\.orchestrator\.core\s+import\s+.*handle_chat.*\r?\n", "", "Multiline")
  # Wstaw import na górze pliku (po ewentualnym shebang/encoding i pierwszych importach)
  $lines = $main2 -split "`r?`n"
  $insertAt = 0
  for ($i=0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^\s*(from|import)\s+") { $insertAt = $i; break }
  }
  $newLines = @()
  for ($i=0; $i -lt $lines.Count; $i++) {
    if ($i -eq $insertAt) { $newLines += $desired }
    $newLines += $lines[$i]
  }
  $final = ($newLines -join "`r`n")
  Set-Content -Path $mainPath -Value $final -Encoding UTF8
  Write-Host "Poprawiono import w main.py -> $desired"
}

Write-Host ""
Write-Host "Gotowe. Teraz uruchom:"
Write-Host "  uvicorn app.main:app --reload --port 8010"
