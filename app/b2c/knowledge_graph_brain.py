
from __future__ import annotations
import json
from pathlib import Path

DATA = Path("data/memory/knowledge_graph.json")

def _ensure():
    DATA.parent.mkdir(parents=True, exist_ok=True)
    if not DATA.exists():
        DATA.write_text("[]", encoding="utf-8")

def _load():
    _ensure()
    return json.loads(DATA.read_text(encoding="utf-8"))

def _save(d):
    DATA.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def add_fact(text: str):
    facts = _load()
    facts.append(text)
    _save(facts)
    return "🧠 Dodano do Knowledge Graph."

def query(entity: str):
    facts = _load()
    res = [f for f in facts if entity.lower() in f.lower()]
    if not res:
        return f"Nie mam wiedzy o {entity}."
    return "Wiem o {}:\n{}".format(entity, "\n".join("• "+x for x in res))
