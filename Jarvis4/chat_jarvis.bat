@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Missing .venv. Run start_jarvis_dev.bat first.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"

REM Match dev token used by the server starter
set DEV_API_KEY=demo-token

echo.
echo [INFO] Jarvis CLI chat (type /exit to quit)
echo.
python tools\chat_cli.py --url http://127.0.0.1:8010 --token %DEV_API_KEY% --user paulina --workspace default --project demo
endlocal
pause
