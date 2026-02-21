@echo off
setlocal enabledelayedexpansion

REM Run tests in a stable way and keep the window open.
set "ROOT=%~dp0.."
pushd "%ROOT%" >nul

echo [INFO] Project root: %CD%

REM Prefer venv python if exists
set "PY=%CD%\.venv\Scripts\python.exe"
if exist "%PY%" (
  echo [INFO] Python cmd: %PY%
) else (
  echo [WARN] No .venv python, trying py -3 / python...
  set "PY=py -3"
  %PY% --version >nul 2>nul
  if errorlevel 1 (
    set "PY=python"
    %PY% --version >nul 2>nul
  )
  if errorlevel 1 (
    echo [ERROR] Could not find Python. Activate venv or install Python.
    goto :end
  )
)

echo [INFO] Checking pip...
%PY% -m pip --version >nul 2>nul
if errorlevel 1 (
  echo [WARN] pip missing, trying ensurepip...
  %PY% -m ensurepip --upgrade
  if errorlevel 1 (
    echo [ERROR] ensurepip failed.
    goto :end
  )
)

echo [INFO] Installing pytest...
%PY% -m pip install -q --disable-pip-version-check pytest
if errorlevel 1 (
  echo [ERROR] Failed to install pytest.
  goto :end
)

echo [INFO] Running tests (tests_sanity)...
%PY% -m pytest -q tests_sanity
set "EC=%ERRORLEVEL%"

if "%EC%"=="0" (
  echo [INFO] OK. Tests passed.
) else (
  echo [ERROR] Tests failed. ExitCode=%EC%
)

:end
popd >nul
echo.
pause
exit /b %EC%
