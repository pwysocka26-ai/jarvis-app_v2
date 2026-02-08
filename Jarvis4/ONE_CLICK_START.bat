@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [INFO] This will start the server in one window and the chat client in another.
start "Jarvis Server" cmd /k "%~dp0start_jarvis_dev.bat"
timeout /t 3 >nul
start "Jarvis Chat" cmd /k "%~dp0chat_jarvis.bat"
endlocal
