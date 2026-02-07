@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM --- Ensure Python 3.11 is available via the Python Launcher (py) ---
where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python Launcher (py) not found. Install Python 3.11 from python.org and make sure it includes the launcher.
  pause
  exit /b 1
)

REM --- Create venv if missing ---
if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual environment (.venv) with Python 3.11...
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv. Verify Python 3.11 is installed.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

echo [INFO] Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed. Try running this script again or check your network/proxy.
  pause
  exit /b 1
)

REM --- DEV auth + talk mode (no Entra needed) ---
set AUTH_MODE=dev
set ENTRA_ENABLED=false
set DEV_API_KEY=demo-token

REM Local LLM (Ollama) settings
set LLM_PROVIDER=ollama
set OLLAMA_HOST=http://127.0.0.1:11434
set OLLAMA_MODEL=llama3.1:8b
set OLLAMA_TIMEOUT=60
set CHAT_MODE=talk

REM --- Run migrations (SQLite by default) ---
echo [INFO] Running Alembic migrations...
python -m alembic upgrade head
if errorlevel 1 (
  echo [WARN] Alembic failed. You can still start the server, but DB features may not work.
)

echo.
echo [INFO] Starting Jarvis:
echo        - API docs:  http://127.0.0.1:8010/docs
echo        - Health:    http://127.0.0.1:8010/v1/health
echo        - Chat:      POST http://127.0.0.1:8010/v1/chat  (Bearer demo-token)
echo.
echo [INFO] To stop the server: press CTRL+C in this window.
echo.

python -m uvicorn app.main:app --port 8010 --reload
endlocal
pause
