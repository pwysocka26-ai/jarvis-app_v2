JARVIS ASGI WORKING (unikalny build: JARVIS_ASGI_WORKING_20260206_194412_VYYSY5)

START (Windows / PowerShell):
1) cd JARVIS_ASGI_WORKING_20260206_194412_VYYSY5
2) python -m venv .venv
3) .\.venv\Scripts\activate
4) pip install -r requirements.txt
5) python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

TEST:
curl -X POST http://127.0.0.1:8010/v1/chat -H "Content-Type: application/json" -d "{\"message\":\"test\"}"
