JARVIS MOBILE v6.1 — OLLAMA BRAIN

Podmień dokładnie:
- Jarvis4/app/api/mobile.py
- Jarvis4/app/services/mobile_service.py
- Jarvis4/app/schemas/mobile.py
- Jarvis4/jarvis-mobile/App.tsx
- Jarvis4/jarvis-mobile/package.json
- Jarvis4/jarvis-mobile/app.json
- Jarvis4/jarvis-mobile/README_START.txt

CO DOSTAJESZ:
- mobilny AI Brain przez lokalną Ollamę podłączoną do backendu
- endpointy backendu:
  - GET  /mobile/ai/health
  - POST /mobile/ai/chat
- pełny kontekst dla modelu: dziś, jutro, priorytety, pamięć, lokalne notatki Brain, tail rozmowy
- action layer z odpowiedzi Ollamy:
  - add_inbox
  - plan_tomorrow
  - save_brain_note
- voice capture nadal działa w Chacie i Inboxie

USTAWIENIA OLLAMA:
- domyślny URL Ollamy w backendzie: http://127.0.0.1:11434
- domyślny model: llama3.1:8b
- możesz zmienić ENV:
  - OLLAMA_URL
  - OLLAMA_MODEL
  - OLLAMA_TIMEOUT

START BACKENDU:
1. uruchom Ollamę
2. test: ollama list
3. backend:
   uvicorn app.mobile_main:app --reload --host 0.0.0.0 --port 8011

START MOBILKI:
1. cd Jarvis4\jarvis-mobile
2. npm install
3. npx expo install expo-speech-recognition expo-notifications @react-native-async-storage/async-storage
4. npx expo run:android

W APLIKACJI:
- Backend URL: np. http://192.168.8.118:8011
- AI Brain: włączony
- Ollama model: np. llama3.1:8b albo mistral:latest

TESTY:
- Settings -> Przetestuj backend
- Settings -> Przetestuj Ollamę
- Chat -> "Co mam dziś najważniejsze?"
- Chat -> "Zaplanuj mi jutro dzień i dodaj focus tam, gdzie mam okna"
- Chat -> "Zapamiętaj, że wolę dentystę rano"
- Inbox -> "jutro 9 dentysta"

UWAGA:
- telefon NIE łączy się bezpośrednio z Ollamą
- telefon gada z backendem FastAPI
- backend dopiero gada z Ollamą lokalnie
- to jest najlepszy układ do developmentu i domowego demo
