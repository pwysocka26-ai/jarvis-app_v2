JARVIS MOBILE v5 — REAL SECOND BRAIN PATCH

Podmień pliki:
- Jarvis4/jarvis-mobile/App.tsx
- Jarvis4/jarvis-mobile/package.json
- Jarvis4/jarvis-mobile/app.json
- Jarvis4/jarvis-mobile/README_START.txt

Co dostajesz w v5:
- Home jako centrum dowodzenia
- Chat z AI i przyciskiem „Zapisz do Brain”
- Plan dnia + AI planner jutra + lokalne przypomnienia
- Brain = backend memory + lokalne notatki second brain
- Inbox = capture z tekstu albo głosu
- prawdziwe voice capture w Chacie i Inboxie
- stabilne przechowywanie ustawień i notatek lokalnie w AsyncStorage

WAŻNE
To jest patch mobilny. Funkcje planner / inbox / memory / priorities dalej korzystają z Twojego backendu /mobile/*.
Lokalny second brain w tej wersji jest po stronie aplikacji mobilnej i nie wymaga zmian backendu.

PO PODMIANIE
1) cd Jarvis4\jarvis-mobile
2) npm install
3) npx expo install expo-speech-recognition expo-notifications
4) npx expo run:android

BACKEND
uvicorn app.mobile_main:app --reload --host 0.0.0.0 --port 8011

TESTY
1) Settings -> ustaw Backend URL
2) Chat -> „Co mam dziś najważniejsze?”
3) Inbox -> „jutro 9 dentysta”
4) Brain -> dodaj notatkę i przypnij ją
5) Plan -> AI planner jutra
6) Chat / Inbox -> kliknij 🎤 Mów
