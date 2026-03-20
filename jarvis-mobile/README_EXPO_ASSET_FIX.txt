JARVIS MOBILE - EXPO ASSET FIX

Podmień:
- Jarvis4/jarvis-mobile/package.json
- Jarvis4/jarvis-mobile/metro.config.js

Ta poprawka dodaje brakującą paczkę expo-asset w wersji zgodnej z Expo SDK 52
oraz przywraca bezpieczny domyślny metro config oparty o expo/metro-config.

Po podmianie uruchom:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
npx expo run:android
