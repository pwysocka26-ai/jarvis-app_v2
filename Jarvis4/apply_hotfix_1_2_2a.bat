@echo off
setlocal
echo [HOTFIX] Applying Jarvis hotfix 1.2.2a (DEV intent A)...
python tools\apply_hotfix_1_2_2a.py
if errorlevel 1 (
  echo [HOTFIX] ERROR. Zobacz komunikat wyzej.
  pause
  exit /b 1
)
echo [HOTFIX] OK.
pause
