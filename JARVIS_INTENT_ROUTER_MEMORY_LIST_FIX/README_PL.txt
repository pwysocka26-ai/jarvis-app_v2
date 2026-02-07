JARVIS — FIX 500 (memory.json ma zły format: lista zamiast słownika)

OBJAW
- Serwer zwraca 500.
- W logu: AttributeError: 'list' object has no attribute 'get'
  (app/memory/store.py -> data.get("history"))

DLACZEGO
W starszej wersji zapisywaliśmy historię jako gołą LISTĘ w pliku JSON.
Nowa wersja oczekuje formatu:
{
  "history": [ ... ],
  "facts": [ ... ]
}

CO ROBI TEN FIX
1) store.py potrafi wczytać STARY format (lista) i automatycznie migruje go
   do formatu słownika przy pierwszym odczycie.
2) chat_cli.py jest odporny na to, że backend zwróci string.

JAK WDROŻYĆ (NAJPROŚCIEJ)
1) Zamknij serwer (CTRL+C w oknie z uvicorn).
2) Podmień pliki w Twoim projekcie:
   - app/memory/store.py  -> (ten z paczki)
   - tools/chat_cli.py    -> (ten z paczki)
3) (Opcjonalnie, jeśli nadal sypie) ZRESETUJ pamięć:
   - usuń plik z danymi pamięci (np. app/data/memory.json albo data/memory.json)
     albo zmień mu nazwę na memory.bak.json
4) Uruchom serwer ponownie.

SZYBKI RESET (PowerShell) — jeśli plik pamięci masz w app\data\memory.json:
  Remove-Item .\app\data\memory.json -ErrorAction SilentlyContinue

