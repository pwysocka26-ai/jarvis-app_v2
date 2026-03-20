Podmień wszystkie pliki z ZIP-a.

Potem uruchom dokładnie:
cd C:\Users\pwyso\Desktop\Jarvis4\jarvis-mobile
adb uninstall com.anonymous.jarvismobile
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
Remove-Item -Recurse -Force android
npm install
npx expo run:android
