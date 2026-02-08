# Run after server is running (in a separate terminal).
. .\.venv\Scripts\Activate.ps1
$env:API_TOKEN="dev-token"
$env:API_URL="http://127.0.0.1:8010/v1/chat"
python tools\chat_cli.py
