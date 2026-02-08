# Starts CLI client (talks to Jarvis API). Requires server running.
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
  . .\.venv\Scripts\Activate.ps1
}
python tools\chat_cli.py
