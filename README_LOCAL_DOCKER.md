# Jarvis – lokalnie (Docker + Postgres/Redis)

Ten wariant jest **cloud‑ready**: lokalnie używasz tych samych klocków, co później w chmurze (Postgres/Redis).

## Wymagania
- Docker Desktop (uruchomiony)
- Python 3.11+

## Start (najprościej)
1. Rozpakuj repo i wejdź do folderu projektu.
2. Uruchom:

```powershell
.\start_local.ps1
```

Skrypt:
- podniesie Postgresa i Redisa (`docker-compose.local.yml`)
- aktywuje/utworzy `.venv`
- zainstaluje zależności
- wykona migracje (`alembic upgrade head`)
- uruchomi serwer na porcie **8010**

## CLI chat
W drugim oknie PowerShell:

```powershell
cd <folder_projektu>
.\.venv\Scripts\Activate.ps1
$env:API_URL="http://127.0.0.1:8010/v1/chat"
$env:API_TOKEN="dev-token"
python tools\chat_cli.py
```

## Konfiguracja
- `.env.local` – ustawienia lokalne (DB, Redis, Ollama)
- `MEMORY_BACKEND=db` przełącza pamięć na bazę (Postgres)

## Szybki test
- Swagger: http://127.0.0.1:8010/docs
