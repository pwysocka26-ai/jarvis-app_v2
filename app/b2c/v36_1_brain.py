
from __future__ import annotations

from typing import Any, Dict, List, Optional

PENDING_FILE = "data/memory/pending_conflict.json"


def _load_pending() -> Optional[Dict[str, Any]]:
    try:
        import json
        from pathlib import Path
        p = Path(PENDING_FILE)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _save_pending(data: Optional[Dict[str, Any]]) -> None:
    try:
        import json
        from pathlib import Path
        p = Path(PENDING_FILE)
        p.parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            if p.exists():
                p.unlink()
            return
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def remember_conflict(event_title: str, event_date: str, event_time: str, conflicts: List[str]) -> None:
    _save_pending({
        "title": event_title,
        "date": event_date,
        "time": event_time,
        "conflicts": conflicts[:8],
    })


def clear_conflict() -> None:
    _save_pending(None)


def conflict_resolver() -> str:
    pending = _load_pending()
    if not pending:
        return "Nie mam teraz aktywnego konfliktu do rozwiązania."
    lines = ["CONFLICT RESOLVER", ""]
    lines.append(f"Nowe wydarzenie: {pending.get('title')} ({pending.get('date')} {pending.get('time')})")
    lines.append("")
    lines.append("Koliduje z:")
    for c in pending.get("conflicts", [])[:8]:
        lines.append(f"• {c}")
    lines.extend([
        "",
        "Możesz teraz wpisać:",
        "• `zachowaj nowe`",
        "• `zachowaj stare`",
        "• `przesuń nowe na HH:MM`",
        "• `wyczyść konflikt`",
    ])
    return "\n".join(lines)


def _load_events() -> List[Dict[str, Any]]:
    try:
        from app.b2c.v34_brain import _load_events
        return _load_events()
    except Exception:
        return []


def _save_events(items: List[Dict[str, Any]]) -> None:
    from app.b2c.v34_brain import _save_events
    _save_events(items)


def _normalize_title(title: str) -> str:
    try:
        from app.b2c.v34_brain import _normalize_title
        return _normalize_title(title)
    except Exception:
        return str(title or "").strip()


def _event_matches(item: Dict[str, Any], title: str, date_iso: str, hhmm: str) -> bool:
    return (
        _normalize_title(str(item.get("title") or "")).lower() == _normalize_title(title).lower()
        and str(item.get("date") or "") == str(date_iso)
        and str(item.get("time") or "") == str(hhmm)
    )


def keep_new() -> str:
    pending = _load_pending()
    if not pending:
        return "Nie mam teraz aktywnego konfliktu do rozwiązania."
    clear_conflict()
    return "✅ Zachowuję nowe wydarzenie. Stare pozostają bez zmian, ale konflikt nadal jest widoczny w kalendarzu."


def keep_old() -> str:
    pending = _load_pending()
    if not pending:
        return "Nie mam teraz aktywnego konfliktu do rozwiązania."
    title = str(pending.get("title") or "")
    date_iso = str(pending.get("date") or "")
    hhmm = str(pending.get("time") or "")
    items = _load_events()
    kept = []
    removed = 0
    for item in items:
        if _event_matches(item, title, date_iso, hhmm) and removed == 0:
            removed += 1
            continue
        kept.append(item)
    _save_events(kept)
    clear_conflict()
    if removed:
        return f"🗑️ Usunęłam nowe wydarzenie: {title} ({date_iso} {hhmm})"
    return "Nie znalazłam nowego wydarzenia do usunięcia."


def move_new(new_hhmm: str) -> str:
    pending = _load_pending()
    if not pending:
        return "Nie mam teraz aktywnego konfliktu do rozwiązania."
    title = str(pending.get("title") or "")
    date_iso = str(pending.get("date") or "")
    old_hhmm = str(pending.get("time") or "")
    items = _load_events()
    updated = False
    for item in items:
        if _event_matches(item, title, date_iso, old_hhmm):
            item["time"] = new_hhmm
            updated = True
            break
    if not updated:
        return "Nie znalazłam nowego wydarzenia do przesunięcia."
    _save_events(items)
    clear_conflict()
    try:
        from app.b2c.v34_brain import _find_time_conflicts
        conflicts = _find_time_conflicts(title, date_iso, new_hhmm, items)
    except Exception:
        conflicts = []
    msg = f"🕒 Przesunęłam nowe wydarzenie na {new_hhmm}: {title}"
    if conflicts:
        msg += "\n⚠️ Nadal widzę możliwy konflikt z: " + ", ".join(conflicts[:5])
    return msg
