from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# We keep memory next to other runtime files (tasks.json etc.)
# Jarvis already uses data/memory/ in many builds.
DATA_DIR = Path("data") / "memory"
MEMORY_FILE = DATA_DIR / "memory.json"

def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load() -> List[Dict[str, Any]]:
    _ensure_dirs()
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []

def _save(items: List[Dict[str, Any]]) -> None:
    _ensure_dirs()
    MEMORY_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def remember(text: str) -> Dict[str, Any]:
    items = _load()
    items.append({"text": text.strip(), "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z"})
    _save(items)
    return {"intent": "memory_remember", "reply": "OK. Zapamiętane.", "meta": {"count": len(items)}}

def list_memory(limit: int = 20) -> Dict[str, Any]:
    items = _load()
    if not items:
        return {"intent": "memory_list", "reply": "Pamięć jest pusta.", "meta": {"count": 0}}
    tail = items[-limit:]
    lines = [f"- {it.get('text','')}" for it in reversed(tail)]
    return {"intent": "memory_list", "reply": "Pamiętam:\n" + "\n".join(lines), "meta": {"count": len(items)}}

def _best_match(query: str, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    # simple token overlap scoring (no embeddings; stable and deterministic)
    q = (query or "").lower()
    q_tokens = {t for t in ''.join((ch if ch.isalnum() else ' ') for ch in q).split() if len(t) >= 3}
    if not q_tokens:
        return items[-1] if items else None
    best = None
    best_score = 0
    for it in reversed(items):
        text = (it.get("text") or "").lower()
        t_tokens = {t for t in ''.join((ch if ch.isalnum() else ' ') for ch in text).split() if len(t) >= 3}
        score = len(q_tokens & t_tokens)
        if score > best_score:
            best_score = score
            best = it
            if best_score >= max(2, len(q_tokens)//2):
                break
    return best

def recall(query: str) -> Dict[str, Any]:
    items = _load()
    if not items:
        return {"intent": "memory_recall", "reply": "Nie mam jeszcze zapisanej pamięci.", "meta": {"count": 0}}
    hit = _best_match(query, items)
    if not hit:
        return {"intent": "memory_recall", "reply": "Nie mam tego w pamięci.", "meta": {"count": len(items)}}
    return {"intent": "memory_recall", "reply": hit.get("text","OK."), "meta": {"count": len(items)}}

def forget(query: str) -> Dict[str, Any]:
    q = (query or "").strip().lower()
    items = _load()
    if not items:
        return {"intent": "memory_forget", "reply": "Pamięć jest pusta.", "meta": {"count": 0}}
    # remove by substring match; if query is short, do nothing
    kept = []
    removed = 0
    for it in items:
        t = (it.get("text") or "").lower()
        if q and q in t:
            removed += 1
        else:
            kept.append(it)
    if removed:
        _save(kept)
        return {"intent": "memory_forget", "reply": f"OK. Usunięto {removed} wpis(ów).", "meta": {"count": len(kept)}}
    return {"intent": "memory_forget", "reply": "Nie znalazłem tego w pamięci.", "meta": {"count": len(items)}}

def handle_memory_message(message: str) -> Optional[Dict[str, Any]]:
    raw = (message or "").strip()
    low = raw.lower()

    # remember
    for prefix in ("zapamiętaj:", "zapamietaj:", "zapamiętaj ", "zapamietaj "):
        if low.startswith(prefix):
            payload = raw.split(":", 1)[1].strip() if ":" in raw else raw[len(prefix):].strip()
            if payload:
                return remember(payload)
            return {"intent": "memory_remember", "reply": "Podaj treść po 'zapamiętaj:'.", "meta": {}}

    # forget
    for prefix in ("zapomnij:", "zapomnij "):
        if low.startswith(prefix):
            payload = raw.split(":", 1)[1].strip() if ":" in raw else raw[len(prefix):].strip()
            if payload:
                return forget(payload)
            return {"intent": "memory_forget", "reply": "Podaj co mam zapomnieć po 'zapomnij:'.", "meta": {}}

    # list
    if low in {"pamięć", "pamiec", "pokaż pamięć", "pokaz pamiec", "co pamiętasz", "co pamietasz"}:
        return list_memory()

    # recall simple questions
    if low.startswith("gdzie ") or low.startswith("kim ") or low.startswith("jaki ") or low.startswith("jaka "):
        return recall(raw)

    return None
