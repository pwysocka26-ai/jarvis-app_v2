from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta, time
from typing import Any, Dict, List, Optional, Tuple

TASKS_FILE = os.path.join("data", "memory", "tasks.json")


def _ensure_dirs() -> None:
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)


def _load() -> Dict[str, Any]:
    _ensure_dirs()
    if not os.path.exists(TASKS_FILE):
        return {"next_id": 1, "tasks": []}
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"next_id": 1, "tasks": []}
        data.setdefault("next_id", 1)
        data.setdefault("tasks", [])
        if not isinstance(data["tasks"], list):
            data["tasks"] = []
        return data
    except Exception:
        # if file is corrupt, do not crash the whole server
        return {"next_id": 1, "tasks": []}


def _atomic_write(data: Dict[str, Any]) -> None:
    _ensure_dirs()
    tmp = TASKS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TASKS_FILE)


def _now() -> datetime:
    return datetime.now()


def _parse_time_hhmm(text: str) -> Optional[time]:
    m = re.search(r"\b([01]?\d|2[0-3])[:\.]([0-5]\d)\b", text)
    if not m:
        return None
    return time(int(m.group(1)), int(m.group(2)))


_WEEKDAYS = {
    "pon": 0, "poniedziałek": 0, "poniedzialek": 0,
    "wt": 1, "wtorek": 1,
    "śr": 2, "sr": 2, "środa": 2, "sroda": 2,
    "czw": 3, "czwartek": 3,
    "pt": 4, "piątek": 4, "piatek": 4,
    "sob": 5, "sobota": 5,
    "nd": 6, "niedz": 6, "niedziela": 6,
}

def _next_weekday(d: date, weekday: int) -> date:
    # returns next occurrence of weekday (including today if same weekday)
    delta = (weekday - d.weekday()) % 7
    return d + timedelta(days=delta)

def _parse_due(text: str) -> Optional[str]:
    """
    Very small Polish date/time parser for MVP:
    - dzisiaj / jutro
    - weekday names (pon/wt/sr/...)
    - optional HH:MM
    Returns ISO string or None.
    """
    low = text.lower()
    t = _parse_time_hhmm(low)
    today = date.today()
    d = None
    if "jutro" in low:
        d = today + timedelta(days=1)
    elif "dzisiaj" in low or "dziś" in low or "dzis" in low:
        d = today
    else:
        for key, wd in _WEEKDAYS.items():
            if re.search(rf"\b{re.escape(key)}\b", low):
                d = _next_weekday(today, wd)
                break
    if d is None and t is None:
        return None
    if d is None:
        d = today
    if t is None:
        # if only date-like words exist, default time 09:00 (can be refined later)
        t = time(9, 0)
    return datetime.combine(d, t).isoformat(timespec="minutes")


def add_task(raw_text: str) -> Dict[str, Any]:
    """
    raw_text: user message e.g. "Dodaj: kupić mleko jutro 18:00"
    """
    text = raw_text.strip()
    # remove command prefix
    text = re.sub(r"^\s*(dodaj|dopisz|wrzu[cć]|utwórz)\s*[:\-]?\s*", "", text, flags=re.I)
    due = _parse_due(text)
    # remove date/time tokens from title (simple cleanup)
    title = re.sub(r"\b(dzisiaj|dziś|dzis|jutro)\b", "", text, flags=re.I).strip()
    title = re.sub(r"\b([01]?\d|2[0-3])[:\.]([0-5]\d)\b", "", title).strip()
    title = re.sub(r"\s{2,}", " ", title).strip()
    if not title:
        title = text

    data = _load()
    tid = int(data.get("next_id") or 1)
    task = {
        "id": tid,
        "title": title,
        "created_at": _now().isoformat(timespec="seconds"),
        "due_at": due,
        "done": False,
        "tags": [],
        "priority": None,
    }
    data["next_id"] = tid + 1
    data["tasks"].append(task)
    _atomic_write(data)

    when = f" (na {due.replace('T',' ')})" if due else ""
    return {"reply": f"✅ Dodane zadanie #{tid}: {title}{when}", "task": task}


def list_tasks(scope: str = "all") -> Dict[str, Any]:
    data = _load()
    tasks = data.get("tasks", [])
    now = _now()

    def is_today(t: Dict[str, Any]) -> bool:
        if not t.get("due_at"):
            return False
        try:
            dt = datetime.fromisoformat(t["due_at"])
            return dt.date() == now.date()
        except Exception:
            return False

    def is_week(t: Dict[str, Any]) -> bool:
        if not t.get("due_at"):
            return False
        try:
            dt = datetime.fromisoformat(t["due_at"])
            start = now.date() - timedelta(days=now.date().weekday())
            end = start + timedelta(days=6)
            return start <= dt.date() <= end
        except Exception:
            return False

    filtered: List[Dict[str, Any]]
    if scope == "today":
        filtered = [t for t in tasks if (not t.get("done")) and is_today(t)]
    elif scope == "week":
        filtered = [t for t in tasks if (not t.get("done")) and is_week(t)]
    else:
        filtered = [t for t in tasks if not t.get("done")]

    if not filtered:
        label = {"today":"na dziś", "week":"na ten tydzień"}.get(scope, "")
        return {"reply": f"✅ Nie masz aktywnych zadań {label}."}

    lines = []
    for t in sorted(filtered, key=lambda x: (x.get("due_at") or "9999", x.get("id", 0))):
        due = ""
        if t.get("due_at"):
            try:
                dt = datetime.fromisoformat(t["due_at"])
                due = dt.strftime(" (%Y-%m-%d %H:%M)")
            except Exception:
                due = f" ({t['due_at']})"
        lines.append(f"#{t['id']}: {t['title']}{due}")

    header = {"today":"📅 Zadania na dziś:", "week":"🗓️ Zadania na tydzień:", "all":"📌 Twoje zadania:"}.get(scope, "📌 Twoje zadania:")
    return {"reply": header + "\n" + "\n".join(lines), "tasks": filtered}


def mark_done(raw_text: str) -> Dict[str, Any]:
    """
    raw_text: "Zrobione 3" or "zrobione #3" or "odhacz 3"
    """
    m = re.search(r"#?\b(\d{1,6})\b", raw_text)
    if not m:
        return {"reply": "Podaj numer zadania, np. `zrobione 3`."}
    tid = int(m.group(1))
    data = _load()
    tasks = data.get("tasks", [])
    for t in tasks:
        if int(t.get("id", -1)) == tid:
            t["done"] = True
            t["done_at"] = _now().isoformat(timespec="seconds")
            _atomic_write(data)
            return {"reply": f"✅ Oznaczone jako zrobione: #{tid} {t.get('title','')}", "task": t}
    return {"reply": f"Nie znalazłam zadania #{tid}."}


def detect_scope(message: str) -> str:
    low = message.lower()
    if "dzis" in low or "dziś" in low or "dzisiaj" in low or "na dziś" in low:
        return "today"
    if "tydzie" in low or "na tydzień" in low:
        return "week"
    return "all"
