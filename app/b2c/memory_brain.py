
from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data/memory")
MEMORY_FILE = DATA_DIR / "memory_brain.json"

def _ensure():
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text("[]", encoding="utf-8")

def _load():
    _ensure()
    return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))

def _save(data):
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _norm(t: str):
    repl = {"ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ż":"z","ź":"z"}
    t = t.lower().strip()
    for a,b in repl.items():
        t = t.replace(a,b)
    t = re.sub(r"[^a-z0-9 ]"," ",t)
    return " ".join(t.split())

def remember(text: str):
    items = _load()
    items.append({"text": text, "ts": datetime.now().isoformat()})
    _save(items)
    return "✅ Zapamiętałem."

def recall(query: str):
    q = _norm(query)
    items = _load()
    out = []
    for i in items:
        nt = _norm(i["text"])
        if q in nt or (len(q) > 3 and q[:-1] in nt):
            out.append(i["text"])
    if not out:
        return f"Nie mam jeszcze nic konkretnego o {query}."
    return "Pamiętam o {}:\n{}".format(query, "\n".join("• "+x for x in out))
