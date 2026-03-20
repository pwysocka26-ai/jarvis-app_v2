Jarvis Mobile v6.8

Ten ZIP zawiera cały App.tsx z poprawkami:
- brak kafelków w oknie Chat
- chat na pełny ekran
- widoczny scrollbar rozmowy
- przycisk Wklej
- zwykłe wiadomości idą do /mobile/ai/chat
- jawne komendy idą do /mobile/inbox

Podmień:
C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile\App.tsx

Potem:
1. jeśli Metro działa -> naciśnij r
2. jeśli nie działa:
   npx expo start --dev-client -c
   a

Jeśli polskie litery dalej nie działają:
- emulator -> Settings -> wyłącz physical keyboard
- użyj klawiatury ekranowej Androida

Jeśli chcesz przycisk Wklej w pełni natywnie:
expo install expo-clipboard
npx expo prebuild
npx expo run:android
