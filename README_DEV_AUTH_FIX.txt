Jarvis – DEV auth fix (removes ENTRA_AUDIENCE requirement)
=========================================================

Problem you saw:
  HTTP 401 / unauthorized with message: "Missing ENTRA_AUDIENCE"

Root cause:
  Backend security dependencies still used Entra/JWT validator.

What this patch does:
  1) Adds: app/security/auth.py   (simple Bearer token auth for DEV)
  2) Replaces: app/security/deps.py to depend on auth.py (NOT Entra)

How to apply:
  - Unzip this archive into your Jarvis4 project root (the folder that contains `app/`).
  - Allow overwrite if prompted.

How to run (PowerShell):
  cd $env:USERPROFILE\Desktop\Jarvis4
  .\.venv\Scripts\activate

  # Start backend (new window)
  $env:DEV_MODE="true"
  $env:API_TOKEN="dev-token"
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

  # Run CLI (another window)
  $env:API_TOKEN="dev-token"
  python tools\chat_cli.py

If you still get ENTRA errors:
  - Search your project for "entra_jwt" or "ENTRA_AUDIENCE".
  - The endpoint dependency must import from app.security.deps (which uses auth.py).

Notes:
  - Token is read from env API_TOKEN; default is "dev-token".
  - DEV_MODE defaults to true; set DEV_MODE=false to disallow dev auth.
