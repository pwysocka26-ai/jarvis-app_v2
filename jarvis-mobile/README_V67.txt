Jarvis Mobile v6.7

Zawiera:
- Chat UI fix: małe chipy, czytelniejsze bąbelki, mniejszy dock
- Real Ollama path: zwykłe wiadomości idą do /mobile/ai/chat, tylko jawne komendy do /mobile/inbox
- Voice checklist / rebuild path w zakładce Ustawienia

Podmień:
C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile\App.tsx

Potem:
1. jeśli Metro działa -> naciśnij r
2. jeśli nie działa:
   npx expo start --dev-client -c
   a

Jeśli Voice nie działa:
expo install expo-speech-recognition
npx expo prebuild
npx expo run:android