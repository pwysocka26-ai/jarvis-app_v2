JARVIS - REAL FIX (v6.1 + Ollama + Kotlin)

Prawdziwa przyczyna:
w projekcie są DWIE wersjonowane definicje Kotlin 1.9.24:
- node_modules/react-native/gradle/libs.versions.toml
- node_modules/@react-native/gradle-plugin/gradle/libs.versions.toml

Dodatkowo expo-modules-core miało domyślny fallback 1.9.24 w:
- node_modules/expo-modules-core/android/ExpoModulesCorePlugin.gradle

To powodowało, że mimo wcześniejszych poprawek build dalej realnie używał 1.9.24,
więc nowa apk nigdy się nie instalowała, a emulator wracał do starego v5.

Ten patch:
1. zostawia App.tsx z v6.1 / Ollamą,
2. hard-pin w android/build.gradle + gradle.properties,
3. poprawia oba version catalogi i ExpoModulesCorePlugin,
4. dodaje postinstall, żeby po npm install poprawka robiła się sama.

Podmień WSZYSTKIE pliki z ZIP-a.

Potem uruchom:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
adb uninstall com.anonymous.jarvismobile
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
Remove-Item -Recurse -Force android
npm install
npx expo run:android

Jeśli chcesz szybciej, po podmianie możesz też tylko:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
node scripts\fix-kotlin-version.js
Remove-Item -Recurse -Force android
npx expo run:android
