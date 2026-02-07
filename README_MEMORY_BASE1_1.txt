Memory Base 1.1 (Jarvis) – patch

Co wnosi:
- trwały profil użytkownika (profile facts) + historia rozmów (JSONL)
- 100% defensywnie: błędy plików / braku katalogów NIE wywalają serwera
- kompatybilność: eksportuje funkcje, które wcześniej 'znikały' (import errors)

Wymagania:
- nic dodatkowego (czysty Python)

Pliki:
- app/orchestrator/memory.py

Dane zapisują się do:
- <root>/data/memory/...
  (możesz zmienić przez env: JARVIS_DATA_DIR)

Env:
- JARVIS_MEMORY_ENABLED=0/1
- JARVIS_DATA_DIR=...
- JARVIS_MEMORY_MAX_TURNS=...
