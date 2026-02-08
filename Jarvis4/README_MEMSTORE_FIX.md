JARVIS - FIX: MemoryStore import + kompatybilność formatu pamięci

Problem:
- ImportError: cannot import name 'MemoryStore' from 'app.memory.store'
- AttributeError: 'list' object has no attribute 'get' (gdy memory.json był listą)

Co robi ta paczka:
1) Dodaje klasę MemoryStore (i alias Memory) w app/memory/store.py
2) Store jest odporny na format:
   - {"history":[...]}  (zalecany)
   - [...]              (stary) -> automatycznie migruje do {"history":[...]}
3) Jeśli plik jest uszkodzony, startuje z pustą historią (nie wywala serwera)

Jak wdrożyć:
- Rozpakuj ZIP w katalogu projektu tak, aby nadpisać: app/memory/store.py
- (Opcjonalnie) usuń stary app/memory/memory.json, żeby zacząć czysto

Test:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
python tools\chat_cli.py
