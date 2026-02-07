# Jarvis3 – Windows starter (DEV)

## LLM offline (Ollama)
Jarvis w tej wersji potrafi odpowiadać "normalnie" przez lokalny model w Ollamie.

1) Sprawdź, że Ollama działa:
   - `ollama --version`
2) Pobierz model (jednorazowo), np.:
   - `ollama pull llama3.1:8b`

Domyślnie starter ustawia:
- `LLM_PROVIDER=ollama`
- `OLLAMA_HOST=http://127.0.0.1:11434`
- `OLLAMA_MODEL=llama3.1:8b`

## Najprostszy sposób (1 klik)
1. Uruchom `ONE_CLICK_START.bat`
2. Otworzą się 2 okna:
   - **Jarvis Server** (API)
   - **Jarvis Chat** (konsola do rozmowy)

> Zatrzymanie serwera: kliknij okno **Jarvis Server** i wciśnij **CTRL+C**.

## Tryb ręczny (2 kroki)
1. Start serwera:
   - uruchom `start_jarvis_dev.bat`
2. Rozmowa:
   - uruchom `chat_jarvis.bat`

## Token (DEV)
W trybie DEV używamy tokena: `demo-token`  
W requestach ustawiasz nagłówek:
`Authorization: Bearer demo-token`

## Adresy
- Docs: http://127.0.0.1:8010/docs
- Health: http://127.0.0.1:8010/v1/health
- Chat (POST): http://127.0.0.1:8010/v1/chat

## Jeśli coś nie działa
- Upewnij się, że masz **Python 3.11** zainstalowany i działa komenda `py -3.11`
- Jeśli port 8010 jest zajęty, zmień `--port 8010` w `start_jarvis_dev.bat`
