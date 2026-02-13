from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Files ---
DATA_DIR = Path("data/memory")
TASKS_FILE = DATA_DIR / "tasks.json"
PENDING_TRAVEL_FILE = DATA_DIR / "pending_travel.json"
PENDING_REMINDER_FILE = DATA_DIR / "pending_reminder.json"

# --- Travel mode parsing ---
TRAVEL_MODES = {
    "samochodem": "samochodem",
    "auto": "samochodem",
    "autem": "samochodem",
    "rowerem": "rowerem",
    "bike": "rowerem",
    "pieszo": "pieszo",
    "piechota": "pieszo",
    "komunikacją": "komunikacją",
    "komunikacja": "komunikacją",
    "zbiorkom": "komunikacją",
    "tramwajem": "komunikacją",
    "metrem": "komunikacją",
    "autobusem": "komunikacją",
}

def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _save_json(path: Path, data: Any) -> None:
    _ensure_dir(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def parse_travel_mode(text: str) -> Optional[str]:
    low = (text or "").strip().lower()
    # exact token
    if low in TRAVEL_MODES:
        return TRAVEL_MODES[low]
    # search word boundary
    for k, v in TRAVEL_MODES.items():
        if re.search(rf"\b{re.escape(k)}\b", low):
            return v
    return None

def _parse_date_time_polish(text: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Very small parser for phrases like:
    - "dziś 19:00"
    - "jutro 8:30"
    - "2026-02-10 19:00"
    Returns (due_date_iso 'YYYY-MM-DD', due_time 'HH:MM', cleaned_text_without_datetime)
    """
    s = (text or "").strip()

    # ISO date optionally + time
    m = re.search(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}:\d{2}))?", s)
    if m:
        d = m.group(1)
        t = m.group(2)
        cleaned = (s[:m.start()] + s[m.end():]).strip(" ,")
        return d, t, cleaned

    today = date.today()
    if re.search(r"\bdzi[śs]\b", s, flags=re.IGNORECASE):
        d = today.isoformat()
        s2 = re.sub(r"\bdzi[śs]\b", "", s, flags=re.IGNORECASE).strip()
    elif re.search(r"\bjutro\b", s, flags=re.IGNORECASE):
        d = (today.fromordinal(today.toordinal() + 1)).isoformat()
        s2 = re.sub(r"\bjutro\b", "", s, flags=re.IGNORECASE).strip()
    else:
        d = None
        s2 = s

    mt = re.search(r"\b(\d{1,2}:\d{2})\b", s2)
    t = mt.group(1) if mt else None
    if t:
        # If user provided only a time (e.g. "23:50") without "dziś/jutro/2026-..",
        # default to today so the task appears in today's plan.
        if d is None:
            d = today.isoformat()
        s2 = (s2[:mt.start()] + s2[mt.end():]).strip(" ,")
    return d, t, s2.strip(" ,")

def load_tasks_db() -> Dict[str, Any]:
    db = _load_json(TASKS_FILE, default={"tasks": []})
    if not isinstance(db, dict) or "tasks" not in db or not isinstance(db.get("tasks"), list):
        db = {"tasks": []}
    return db

def save_tasks_db(db: Dict[str, Any]) -> None:
    _save_json(TASKS_FILE, db)

def _next_id(tasks: List[Dict[str, Any]]) -> int:
    ids = [t.get("id") for t in tasks if isinstance(t.get("id"), int)]
    return (max(ids) + 1) if ids else 1

def add_task(raw: str) -> Dict[str, Any]:
    """Adds a task. Accepts optional travel mode anywhere in text."""
    raw = (raw or "").strip()
    travel = parse_travel_mode(raw)

    due_date, due_time, rest = _parse_date_time_polish(raw)
    title = rest.strip()
    # normalize separators
    title = re.sub(r"\s+", " ", title).strip(" ,")

    # if user wrote "... , samochodem" treat as travel mode and remove from title
    if travel:
        title = re.sub(rf"(?:,|\s)+{re.escape(travel)}\s*$", "", title, flags=re.IGNORECASE).strip(" ,")

    # Optional location parsing: if user uses comma-separated format
    # e.g. "dentysta, Niemcewicza 25, Warszawa" -> title="dentysta", location="Niemcewicza 25, Warszawa"
    location = None
    if "," in title:
        parts = [p.strip() for p in title.split(",") if p.strip()]
        if len(parts) >= 2:
            title = parts[0]
            location = ", ".join(parts[1:])

    db = load_tasks_db()
    tasks = db["tasks"]
    task_id = _next_id(tasks)

    due_at = None
    if due_date and due_time:
        due_at = f"{due_date}T{due_time}"
    elif due_date:
        due_at = due_date

    task = {
        "id": task_id,
        "title": title if title else "(bez tytułu)",
        "created_at": _now_iso(),
        "due_at": due_at,
        "done": False,
        "tags": [],
        "priority": None,
        "location": location,
        "reminder_at": None,
        "reminder_enabled": False,
        "travel_mode": travel,  # None if not set
    }
    tasks.append(task)
    save_tasks_db(db)

    reply = f"✅ Dodane zadanie #{task_id}: {task['title']}"
    if due_at:
        reply += f" (na {due_at})"
    if travel:
        reply += f" — dojazd: {travel}"
    return {"reply": reply, "task": task}

def list_tasks_for_date(d: str) -> List[Dict[str, Any]]:
    db = load_tasks_db()
    out = []
    for t in db["tasks"]:
        due = (t.get("due_at") or "")
        if due.startswith(d):
            out.append(t)
    # sort by time if present
    def key(t):
        due = t.get("due_at") or ""
        return due
    out.sort(key=key)
    return out

def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            return t
    return None

def update_task(task_id: int, **fields: Any) -> Optional[Dict[str, Any]]:
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            t.update(fields)
            save_tasks_db(db)
            return t
    return None

# --- Pending travel (no conversation_state.json needed) ---
def get_pending_travel() -> Optional[Dict[str, Any]]:
    data = _load_json(PENDING_TRAVEL_FILE, default=None)
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("task_id"), int):
        return None
    return data

def set_pending_travel(task_id: int, *, created_from: str = "rano") -> None:
    _save_json(PENDING_TRAVEL_FILE, {"task_id": task_id, "created_from": created_from, "created_at": _now_iso()})

def clear_pending_travel() -> None:
    if PENDING_TRAVEL_FILE.exists():
        try:
            PENDING_TRAVEL_FILE.unlink()
        except Exception:
            _save_json(PENDING_TRAVEL_FILE, None)


# --- Pending reminder (yes/no) ---
def get_pending_reminder() -> Optional[Dict[str, Any]]:
    data = _load_json(PENDING_REMINDER_FILE, default=None)
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("task_id"), int):
        return None
    if not isinstance(data.get("reminder_at"), str):
        return None
    return data

def set_pending_reminder(task_id: int, reminder_at: str, *, created_from: str = "rano") -> None:
    _save_json(PENDING_REMINDER_FILE, {"task_id": task_id, "reminder_at": reminder_at, "created_from": created_from, "created_at": _now_iso()})

def clear_pending_reminder() -> None:
    if PENDING_REMINDER_FILE.exists():
        try:
            PENDING_REMINDER_FILE.unlink()
        except Exception:
            _save_json(PENDING_REMINDER_FILE, None)

def parse_yes_no(text: str) -> Optional[bool]:
    low = (text or "").strip().lower()
    yes = {"tak", "t", "ok", "okej", "jasne", "pewnie", "y", "yes"}
    no  = {"nie", "n", "no", "nah", "cancel", "anuluj"}
    if low in yes:
        return True
    if low in no:
        return False
    return None

def set_task_reminder(task_id: int, reminder_at: str, enabled: bool) -> Dict[str, Any]:
    t = update_task(task_id, reminder_at=reminder_at, reminder_enabled=enabled)
    if not t:
        return {"ok": False, "reply": f"Nie znalazłem zadania #{task_id}."}
    if enabled:
        return {"ok": True, "reply": f"⏰ Ustawiłem przypomnienie dla zadania #{task_id} na **{reminder_at}**."}
    return {"ok": True, "reply": f"OK, bez przypomnienia dla zadania #{task_id}."}

def apply_travel_mode_to_task_id(mode: str, task_id: int) -> Dict[str, Any]:
    mode = parse_travel_mode(mode) or mode
    t = update_task(task_id, travel_mode=mode)
    if not t:
        return {"ok": False, "reply": f"Nie znalazłem zadania #{task_id}.", "task_id": task_id}
    return {"ok": True, "reply": f"✅ Ustawiono dojazd dla zadania #{task_id}: {mode}", "task": t}


def apply_travel_mode_to_pending(message: str) -> dict | None:
    """Handle user's transport choice for a previously requested travel-mode decision.

    - If there is no pending travel decision -> return None (router may continue).
    - If there is pending but message is not a recognized choice -> return a short reminder (and DO NOT fall back to LLM).
    """
    pending = get_pending_travel()
    if not pending:
        return None

    msg = (message or "").strip().lower()

    # Accept both words and numeric shortcuts
    mode_map = {
        "1": "walking",
        "pieszo": "walking",
        "na piechote": "walking",
        "na piechotę": "walking",
        "2": "transit",
        "komunikacja": "transit",
        "tramwaj": "transit",
        "metro": "transit",
        "autobusem": "transit",
        "3": "car",
        "samochodem": "car",
        "auto": "car",
        "samochod": "car",
        "samochód": "car",
    }

    if msg not in mode_map:
        return {"reply": "Wybierz środek transportu: 1) pieszo  2) komunikacja  3) samochód"}

    task_id = pending.get("task_id")
    if not task_id:
        clear_pending_travel()
        return {"reply": "Ups — nie widzę zadania do dojazdu. Wpisz 'rano' i spróbuj ponownie."}

    mode = mode_map[msg]
    ok = apply_travel_mode_to_task_id(mode, task_id)
    clear_pending_travel()

    if not ok:
        return {"reply": "Nie udało się ustawić trybu dojazdu dla tego zadania."}

    # MVP: prosty, deterministyczny szacunek czasu wyjścia (bez zewnętrznych API)
    task = get_task(int(task_id)) or {}
    due_at = task.get("due_at")

    mins_by_mode = {"walking": 60, "transit": 40, "car": 25}
    travel_min = mins_by_mode.get(mode, 30)
    buffer_min = 10

    leave_line = ""
    try:
        from datetime import datetime, timedelta
        if due_at:
            s = str(due_at).replace("T", " ")
            dt = datetime.fromisoformat(s)
            leave = dt - timedelta(minutes=travel_min + buffer_min)
            leave_line = (
                f"\n\n⏱️ Proponowane wyjście: **{leave.strftime('%H:%M')}** "
                f"(dojazd ~{travel_min} min + {buffer_min} min zapasu)"
            )
    except Exception:
        pass

    return {"reply": f"✅ Ustawione: {mode}.{leave_line}"}