@echo off
REM Starts Jarvis API (uvicorn) on http://127.0.0.1:8010

if exist ".\.venv\Scripts\activate.bat" call ".\.venv\Scripts\activate.bat"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
