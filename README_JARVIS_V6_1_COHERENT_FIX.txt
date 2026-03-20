JARVIS V6.1 OLLAMA - COHERENT FIX

Podmień WSZYSTKIE pliki z tego ZIP-a.

Ten patch robi 3 rzeczy naraz:
1. przywraca frontend v6.1 (zamiast starego v5),
2. naprawia build Android (expo-asset, index.js, metro.config.js, Kotlin 1.9.25),
3. zostawia backendowe endpointy Ollamy:
   - GET /mobile/ai/health
   - POST /mobile/ai/chat

Po podmianie uruchom dokładnie:

Backend:
cd C:\Users\pwyso\Desktop\Jarvis4
uvicorn app.mobile_main:app --reload --host 0.0.0.0 --port 8011

Mobile:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
adb uninstall com.anonymous.jarvismobile
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
Remove-Item -Recurse -Force android
npm install
npx expo run:android

Test po starcie:
1. W aplikacji powinno być widać v6.1 / AI / Ollama, nie stare v5.
2. W PowerShellu:
   curl http://127.0.0.1:8011/mobile/ai/health
3. W Chat:
   Co mam dziś najważniejsze?

Jeśli curl zwróci JSON z available=true, Ollama backend działa.
