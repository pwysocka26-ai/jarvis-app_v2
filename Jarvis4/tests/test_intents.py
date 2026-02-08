# Minimalne testy „dymne” dla klasyfikacji intentów.
# Uruchom: python tests/test_intents.py

from app.intent.router import classify_intent

cases = [
    ("Hej", "greet"),
    ("help", "help"),
    ("zapamiętaj: lubię Tatry", "remember"),
    ("mam na imię Paulina", "remember"),
    ("jak mam na imię?", "recall_name"),
    ("pokaż pamięć", "show_memory"),
    ("wyczyść pamięć", "clear_memory"),
    ("status", "status"),
    ("ok", "smalltalk"),
    ("opowiedz mi o Tatrach", "chat"),
]

ok = True
for text, expected in cases:
    got = classify_intent(text)
    if got != expected:
        ok = False
        print(f"FAIL: {text!r} -> {got!r} (expected {expected!r})")

print("OK" if ok else "FAILED")
