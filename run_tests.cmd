@echo off
setlocal
REM Jarvis - idiotoodporny runner testów (Windows)
REM Double-click albo odpal w CMD.

REM Przejdź do folderu projektu (tam gdzie jest ten plik)
cd /d "%~dp0"

REM Uruchom PowerShell z pominięciem ExecutionPolicy (bez zmiany ustawień systemu)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\run_tests.ps1"
if errorlevel 1 (
  echo.
  echo ❌ Testy nie przeszly. Zobacz komunikat powyzej.
  exit /b 1
)
echo.
echo ✅ OK
