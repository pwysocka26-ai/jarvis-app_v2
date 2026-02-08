JARVIS – Intent Router (B+C+D) GOTOWIEC

Co zawiera:
- app/memory/store.py – odporny magazyn pamięci (history + facts)
- app/intent/router.py – intent router z:
  * remember/forget
  * profile_set/profile_show
  * goal_set/goal_show
  * dynamiczny system prompt (_build_system_hint)

Instalacja:
1) Rozpakuj ZIP w katalogu projektu Jarvis4.
2) Nadpisz pliki:
   - app/memory/store.py
   - app/intent/router.py
3) Uruchom serwer:
   python -m app.main
4) Uruchom CLI:
   python tools/chat_cli.py

Test komendy:
- profil: city=Warszawa; age=29; job=PM
- pokaż profil
- cel: Zbudować Jarvisa B2C (asystent w chmurze)
- pokaż cele
- zapamiętaj: lubię Tatry
- zapomnij: Tatry
