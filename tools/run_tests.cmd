@echo off
setlocal EnableExtensions

REM Always run from project root to avoid pytest collecting outside the repo.
cd /d "%~dp0\.."

REM Make test runs deterministic and production-safe.
set JARVIS_ENV=test
set JARVIS_DISABLE_SCHEDULER=1
if "%API_TOKEN%"=="" set API_TOKEN=dev-token

REM Default: run the safety test suite only. Pass "full" to run everything.
if /I "%1"=="full" (
  python -m pytest -q --disable-warnings --maxfail=1 --cov=app --cov-report=term-missing --cov-report=html
) else (
  python -m pytest -q tests_sanity --disable-warnings --maxfail=1
)

endlocal