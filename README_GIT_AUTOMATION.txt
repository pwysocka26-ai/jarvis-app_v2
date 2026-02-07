Jarvis4 — Git automation scripts

Zawartość:
- setup_git.ps1  -> inicjalizacja repo, .gitignore, .gitkeep, pierwszy commit + tag v0.1.0
- release.ps1    -> automatyczne wersjonowanie (patch/minor/major): commit + tag

Jak użyć:
1) Skopiuj pliki do katalogu Jarvis4 (obok app/, tools/, itd.)
2) PowerShell w Jarvis4:
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   .\setup_git.ps1
3) Po zmianach:
   .\release.ps1 patch
   .\release.ps1 minor
   .\release.ps1 major

Cofanie:
- git checkout v0.1.0
- git checkout main

Uwagi:
- .env i data/memory są ignorowane celowo (sekrety i dane lokalne).
