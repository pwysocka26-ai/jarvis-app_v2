JARVIS MOBILE - KOTLIN FIX

Podmień te pliki:
- Jarvis4/jarvis-mobile/android/build.gradle
- Jarvis4/jarvis-mobile/android/gradle.properties

Ta poprawka wymusza Kotlin 1.9.24, zgodny z Expo SDK 52 i expo-modules-core 2.2.3.
Naprawia błąd:
'Compose Compiler requires Kotlin 1.9.25 but you appear to be using Kotlin 1.9.24'
oraz compileDebugKotlin w expo-modules-core.

Po podmianie uruchom:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
Remove-Item -Recurse -Force android\.gradle -ErrorAction SilentlyContinue
npx expo run:android
