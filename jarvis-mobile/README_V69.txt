Jarvis Mobile v6.9 — pełna aplikacja + voice integration

Zmiany w tym ZIP-ie:
- wraca pełny App.tsx Jarvisa
- voice jest wpięty w istniejący przycisk 🎤 Voice w Chat i Inbox
- flow: klik → start nasłuchu → wynik wpada do inputa → opcjonalny auto-send
- statusy: Słucham... / Przetwarzam... / Gotowe.
- pełnoekranowy chat, wszystkie zakładki, test backendu i test Ollamy

Podmień:
C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile\App.tsx

Uruchomienie na telefonie:
1. cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
2. npx expo run:android --device
3. wybierz telefon
4. po instalacji uruchom apkę Jarvis Mobile na telefonie

Do developmentu:
npx expo start --dev-client

Uwaga:
Expo Go nie obsługuje expo-speech-recognition.
