from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "memory"
INBOX_FILE = DATA_DIR / "inbox.json"

def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def _read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _write_json(path: Path, data) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def load_inbox() -> List[Dict[str, Any]]:
    data = _read_json(INBOX_FILE, default=[])
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "id": int(item.get("id") or 0),
                "text": text,
                "created_at": str(item.get("created_at") or _now_iso()),
                "kind": str(item.get("kind") or "note"),
            }
        )
    return out

def save_inbox(items: List[Dict[str, Any]]) -> None:
    _write_json(INBOX_FILE, items)

def _next_id(items: List[Dict[str, Any]]) -> int:
    max_id = 0
    for it in items:
        try:
            max_id = max(max_id, int(it.get("id") or 0))
        except Exception:
            continue
    return max_id + 1

def add_inbox(text: str, *, kind: str = "note") -> Dict[str, Any]:
    clean = (text or "").strip()
    if not clean:
        return {"ok": False, "reply": "Nie mam czego zapisać do Inbox."}
    items = load_inbox()
    item = {
        "id": _next_id(items),
        "text": clean,
        "created_at": _now_iso(),
        "kind": kind or "note",
    }
    items.append(item)
    save_inbox(items)
    return {"ok": True, "item": item, "reply": f"🧠 Zapisano do Inbox #{item['id']}: {item['text']}"}

def list_inbox() -> Dict[str, Any]:
    items = load_inbox()
    if not items:
        return {"ok": True, "items": [], "reply": "Inbox jest pusty."}
    lines = ["INBOX", ""]
    for idx, item in enumerate(items, start=1):
        lines.append(f"{idx}. {item['text']}")
    return {"ok": True, "items": items, "reply": "\n".join(lines)}

def delete_inbox_by_live_number(n: int) -> Dict[str, Any]:
    items = load_inbox()
    if n < 1 or n > len(items):
        return {"ok": False, "reply": f"Nie ma wpisu #{n} w Inbox."}
    removed = items.pop(n - 1)
    save_inbox(items)
    return {"ok": True, "removed": removed, "reply": f"🗑 Usunięto z Inbox #{n}: {removed['text']}"}

def get_inbox_by_live_number(n: int) -> Optional[Dict[str, Any]]:
    items = load_inbox()
    if n < 1 or n > len(items):
        return None
    return items[n - 1]

def clear_inbox() -> Dict[str, Any]:
    items = load_inbox()
    count = len(items)
    save_inbox([])
    return {"ok": True, "reply": f"🧹 Wyczyszczono Inbox ({count}).", "count": count}
