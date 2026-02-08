# set_sqlite_env.ps1
# Ustawia DATABASE_URL + MEMORY_BACKEND na SQLite (lokalny plik jarvis.db) w pliku .env.local.
# Jeśli PowerShell blokuje uruchomienie (Unsigned), użyj: scripts\set_sqlite_env.cmd

$ErrorActionPreference = "Stop"

$root = Get-Location
$envFile = Join-Path $root ".env.local"

if (!(Test-Path $envFile)) {
  throw "Nie znaleziono pliku .env.local w: $root. Wejdź do katalogu repo (np. Desktop\Jarvis4) i uruchom ponownie."
}

$content = Get-Content $envFile -Raw

# SQLite URL: relative file in repo root
$sqliteUrl = "sqlite:///./jarvis.db"

function Upsert-Line([string]$text, [string]$key, [string]$value) {
  if ($text -match "^(?m)\s*$([regex]::Escape($key))\s*=") {
    return [regex]::Replace($text, "^(?m)\s*$([regex]::Escape($key))\s*=.*$", "$key=$value")
  }
  return $text.TrimEnd() + "`r`n$key=$value`r`n"
}

$new = $content
$new = Upsert-Line $new "DATABASE_URL" $sqliteUrl
$new = Upsert-Line $new "MEMORY_BACKEND" "sqlite"

Set-Content -Path $envFile -Value $new -Encoding UTF8
Write-Host "OK: Ustawiono DATABASE_URL + MEMORY_BACKEND=sqlite w .env.local" -ForegroundColor Green
Write-Host "DATABASE_URL=$sqliteUrl" -ForegroundColor Green
