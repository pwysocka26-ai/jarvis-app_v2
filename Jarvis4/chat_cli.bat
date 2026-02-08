@echo off
REM Starts CLI client (talks to Jarvis API). Requires server running.
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python tools\chat_cli.py
