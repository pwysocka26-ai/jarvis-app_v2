Jarvis4 – Git safety update

Co dodaje ta paczka:
1) start_jarvis.ps1: automatycznie przełącza repo na branch 'work' (jeśli nie istnieje – tworzy).
2) .vscode/settings.json + .vscode/tasks.json:
   - włączone dekoracje Git
   - task: "Jarvis: pokaż aktualny branch" (Terminal -> Run Task)

Jak zastosować:
- Skopiuj plik start_jarvis.ps1 do katalogu Jarvis4 (nadpisz).
- Skopiuj folder .vscode do Jarvis4 (jeśli istnieje – nadpisz pliki w środku).

Użycie:
- Start Jarvisa: .\start_jarvis.ps1
- Sprawdź branch: git status
- W VS Code: uruchom task "Jarvis: pokaż aktualny branch"
