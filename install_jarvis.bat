@echo off
REM One-time installer for Windows.
REM Creates .venv and installs Python deps.

python -m venv .venv
call .\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo OK. Next: copy .env.example to .env and run start_server.bat
pause
