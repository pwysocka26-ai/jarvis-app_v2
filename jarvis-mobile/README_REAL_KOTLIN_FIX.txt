JARVIS - REAL KOTLIN FIX

Prawdziwa przyczyna błędu:
node_modules/react-native/gradle/libs.versions.toml nadal przypinał:
kotlin = "1.9.24"

Expo SDK 52 + expo-modules-core + Compose Compiler 1.5.15 wymagają tutaj 1.9.25.
Dopóki ten plik zostaje na 1.9.24, build nowej wersji się wywala i emulator odpala ostatnią starą apkę v5.

Podmień wszystkie pliki z ZIP-a.

Jeśli node_modules już masz:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
adb uninstall com.anonymous.jarvismobile
Remove-Item -Recurse -Force android
npx expo run:android

Jeśli chcesz na czysto:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
adb uninstall com.anonymous.jarvismobile
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
Remove-Item -Recurse -Force android
npm install
npx expo run:android

Po npm install skrypt postinstall sam ponownie naprawi Kotlin do 1.9.25.
