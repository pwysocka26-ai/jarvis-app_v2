
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

STATE_FILE = Path("data/memory/personal_memory.json")


def _ensure_dir() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"facts": []}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            facts = data.get("facts", [])
            if isinstance(facts, list):
                return {"facts": facts}
    except Exception:
        pass
    return {"facts": []}


def _save_state(data: Dict[str, Any]) -> None:
    _ensure_dir()
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    repl = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ż": "z", "ź": "z",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def remember_fact(text: str) -> str:
    fact = (text or "").strip().strip(".")
    if not fact:
        return "Podaj, co mam zapamiętać."
    data = _load_state()
    facts = data["facts"]
    nf = _normalize(fact)
    for existing in facts:
        if _normalize(str(existing)) == nf:
            return "Już to pamiętam."
    facts.append(fact)
    _save_state(data)
    return f"🧠 Zapamiętałam: {fact}"


def recall_all() -> str:
    data = _load_state()
    facts = [str(x).strip() for x in data.get("facts", []) if str(x).strip()]
    if not facts:
        return "Nie mam jeszcze zapisanej pamięci osobistej."
    lines = ["PERSONAL MEMORY", ""]
    lines.extend(f"• {fact}" for fact in facts[:20])
    return "\n".join(lines)


def recall_about_me() -> str:
    data = _load_state()
    facts = [str(x).strip() for x in data.get("facts", []) if str(x).strip()]
    if not facts:
        return "Nie wiem jeszcze o Tobie nic konkretnego."
    lines = ["To o Tobie pamiętam:", ""]
    lines.extend(f"• {fact}" for fact in facts[:12])
    return "\n".join(lines)


def recall_match(query: str) -> str:
    q = _normalize(query)
    if not q:
        return "Podaj, czego mam poszukać w pamięci."
    data = _load_state()
    facts = [str(x).strip() for x in data.get("facts", []) if str(x).strip()]
    found: List[str] = []
    for fact in facts:
        nf = _normalize(fact)
        if q in nf or any(tok and tok in nf for tok in q.split()):
            found.append(fact)
    if not found:
        return f"Nie mam jeszcze nic konkretnego o: {query}"
    lines = [f"Pamiętam o „{query}”:", ""]
    lines.extend(f"• {fact}" for fact in found[:10])
    return "\n".join(lines)


def forget_fact(query: str) -> str:
    q = _normalize(query)
    data = _load_state()
    facts = [str(x).strip() for x in data.get("facts", []) if str(x).strip()]
    kept = []
    removed = []
    for fact in facts:
        nf = _normalize(fact)
        if q and (q in nf or any(tok and tok in nf for tok in q.split())):
            removed.append(fact)
        else:
            kept.append(fact)
    if not removed:
        return "Nie znalazłam takiej rzeczy w pamięci."
    data["facts"] = kept
    _save_state(data)
    if len(removed) == 1:
        return f"🗑️ Usunęłam z pamięci: {removed[0]}"
    return f"🗑️ Usunęłam z pamięci {len(removed)} wpisy."


def memory_brief() -> str:
    data = _load_state()
    facts = [str(x).strip() for x in data.get("facts", []) if str(x).strip()]
    lines = ["MEMORY BRAIN v2", ""]
    lines.append(f"Liczba faktów: {len(facts)}")
    if facts:
        lines.extend(["", "Najważniejsze rzeczy, które pamiętam:"])
        lines.extend(f"• {fact}" for fact in facts[:8])
    else:
        lines.extend(["", "Pamięć osobista jest jeszcze pusta."])
    return "\n".join(lines)
