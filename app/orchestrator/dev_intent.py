import re
from typing import Optional

# Frazy, które traktujemy jako "developer intent"
DEV_PATTERNS = [
    r"\bpracuj[ęe]\s+nad\s+jarvisem\b",
    r"\brozwijam\s+jarvisa\b",
    r"\bulepszam\s+jarvisa\b",
    r"\bpopraw(ia|ić|my)\s+jarvisa\b",
    r"\bzmi(e|ę)ń\s+(twoje\s+)?dzia(ł|l)anie\b",
    r"\bpopraw\s+(twoje\s+)?reakcj(e|ę)\b",
    r"\bdebug(uj|owanie)?\b",
    r"\btryb\s+dev\b",
]

_DEV_RE = re.compile("|".join(f"(?:{p})" for p in DEV_PATTERNS), re.IGNORECASE)

def is_dev_intent(text: Optional[str]) -> bool:
    if not text:
        return False
    return _DEV_RE.search(text.strip()) is not None

def dev_intent_reply(user_name: str = "Paulina") -> str:
    # deterministyczna odpowiedź – bez wywołania LLM
    return (
        f"Jasne, {user_name}. Widzę, że pracujesz nad rozwojem Jarvisa (tryb DEV).\n"
        "Powiedz proszę, co dokładnie chcesz zrobić:\n"
        "1) Pamięć (co zapamiętywać i jak odpytywać)\n"
        "2) Narzędzia / komendy (np. /remember, /forget, /profile)\n"
        "3) Styl odpowiedzi (krócej/dłużej, bardziej technicznie)\n"
        "4) Integracje (Ollama / API / GUI)\n"
        "Napisz numer (1–4) albo opisz zadanie jednym zdaniem."
    )
