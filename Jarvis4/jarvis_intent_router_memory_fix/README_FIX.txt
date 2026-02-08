JARVIS — fix błędu: AttributeError: 'list' object has no attribute 'get'

Objaw:
- Serwer zwraca 500
- Traceback kończy się na: app/memory/store.py ... data.get("history") ... a data jest listą

Przyczyna:
Masz stary format pliku pamięci (JSON), gdzie cały plik był listą wiadomości, a nowszy kod oczekuje słownika:
{ "facts": [...], "history": [...] }

Co robi poprawka:
- MemoryStore._read() wykrywa stary format (listę) i automatycznie migruje go do nowego formatu.

Jak wgrać:
1) Skopiuj plik:
   app/memory/store.py
   do swojego projektu (nadpisz istniejący).
2) (Opcjonalnie) Skopiuj tools/chat_cli.py jeśli chcesz, żeby CLI było odporniejsze na nietypowe odpowiedzi.
3) Uruchom ponownie serwer.

Jeśli chcesz „twardy reset” pamięci:
- usuń plik: app/data/memory.json (lub gdziekolwiek wskazuje ścieżka pamięci)

