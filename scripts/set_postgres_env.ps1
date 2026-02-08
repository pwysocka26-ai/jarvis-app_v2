# set_postgres_env.ps1
# Ustawia DATABASE_URL + MEMORY_BACKEND na Postgres (Docker) w pliku .env.local w katalogu projektu.
# Jeśli PowerShell blokuje uruchomienie (Unsigned), użyj: scripts\set_postgres_env.cmd

$ErrorActionPreference = "Stop"

$root = Get-Location
$envFile = Join-Path $root ".env.local"

if (!(Test-Path $envFile)) {
  throw "Nie znaleziono pliku .env.local w: $root. Wejdź do katalogu repo (np. Desktop\Jarvis4) i uruchom ponownie."
}

$content = Get-Content $envFile -Raw

$pgUrl = "postgresql+psycopg://jarvis:jarvis@127.0.0.1:5432/jarvis"

function Upsert-Line([string]$text, [string]$key, [string]$value) {
  if ($text -match "^(?m)\s*$([regex]::Escape($key))\s*=") {
    return [regex]::Replace($text, "^(?m)\s*$([regex]::Escape($key))\s*=.*$", "$key=$value")
  }
  return $text.TrimEnd() + "`r`n$key=$value`r`n"
}

$new = $content
$new = Upsert-Line $new "DATABASE_URL" $pgUrl
$new = Upsert-Line $new "MEMORY_BACKEND" "db"

Set-Content -Path $envFile -Value $new -Encoding UTF8
Write-Host "OK: Ustawiono DATABASE_URL + MEMORY_BACKEND=db w .env.local" -ForegroundColor Green
Write-Host "DATABASE_URL=$pgUrl" -ForegroundColor Green
