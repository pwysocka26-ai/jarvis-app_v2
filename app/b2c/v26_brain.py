
from __future__ import annotations

import json
from pathlib import Path
from datetime import date, datetime
from typing import Any, Dict, List, Optional

STATE_FILE = Path("data/memory/context_brain.json")


def _ensure_dir() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(data: Dict[str, Any]) -> None:
    _ensure_dir()
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_min() -> int:
    now = datetime.now()
    return now.hour * 60 + now.minute


def _fmt_min(minutes: int) -> str:
    h, m = divmod(max(0, int(minutes)), 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"


def _today_tasks(tasks_mod) -> List[Dict[str, Any]]:
    try:
        tasks = tasks_mod.list_tasks_for_date(date.today()) or []
    except Exception:
        tasks = []
    return [t for t in tasks if isinstance(t, dict) and not bool(t.get("done"))]


def _task_title(task: Dict[str, Any]) -> str:
    title = str(task.get("title") or task.get("text") or "").strip()
    if title.lower().startswith("bez godziny "):
        title = title[len("bez godziny "):].strip()
    return title or "(bez tytułu)"


def _task_due_min(task: Dict[str, Any]) -> Optional[int]:
    due = str(task.get("due_at") or "")
    if "T" not in due:
        return None
    try:
        hhmm = due.split("T", 1)[1][:5]
        hh, mm = hhmm.split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return None


def _task_duration(task: Dict[str, Any]) -> int:
    try:
        val = int(task.get("duration_min") or 30)
        return max(5, val)
    except Exception:
        return 30


def _task_priority(task: Dict[str, Any]) -> int:
    try:
        return int(task.get("priority") or 2)
    except Exception:
        return 2


def set_context(key: str, value: Any) -> str:
    state = _load_state()
    state[key] = value
    _save_state(state)
    if key == "available_minutes":
        return f"⏱ Ustawiłam dostępny czas: {_fmt_min(int(value))}."
    labels = {
        "place": "miejsce",
        "mode": "tryb",
        "state": "stan",
    }
    return f"✅ Ustawiłam {labels.get(key, key)}: {value}"


def clear_context() -> str:
    _save_state({})
    return "🧹 Wyczyściłam kontekst dnia."


def context_summary() -> str:
    state = _load_state()
    if not state:
        return "Nie masz ustawionego aktywnego kontekstu."
    lines = ["CONTEXT BRAIN", ""]
    if state.get("place"):
        lines.append(f"Miejsce: {state['place']}")
    if state.get("mode"):
        lines.append(f"Tryb: {state['mode']}")
    if state.get("state"):
        lines.append(f"Stan: {state['state']}")
    if state.get("available_minutes"):
        lines.append(f"Dostępny czas: {_fmt_min(int(state['available_minutes']))}")
    return "\n".join(lines)


def suggest_by_context(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    state = _load_state()
    if not tasks:
        return "Nie masz dziś aktywnych zadań."

    now_min = _now_min()
    available = None
    try:
        if state.get("available_minutes") is not None:
            available = int(state["available_minutes"])
    except Exception:
        available = None

    untimed = [t for t in tasks if _task_due_min(t) is None]
    timed = sorted([t for t in tasks if _task_due_min(t) is not None], key=lambda t: (_task_due_min(t) or 10**9, _task_priority(t), int(t.get("id") or 0)))

    for t in timed:
        due = _task_due_min(t)
        if due is None:
            continue
        delta = due - now_min
        if 0 <= delta <= 20:
            return f"Najbliższy kontekstowy krok: {_task_title(t)} (start za {_fmt_min(delta)})."

    pool = untimed[:] if untimed else timed[:]
    if available is not None:
        fitting = [t for t in pool if _task_duration(t) <= available]
        if fitting:
            fitting.sort(key=lambda t: (_task_priority(t), _task_duration(t), int(t.get("id") or 0)))
            best = fitting[0]
            return f"W Twoim kontekście najlepiej pasuje: {_task_title(best)} (~{_task_duration(best)} min, p{_task_priority(best)})."

    if untimed:
        untimed.sort(key=lambda t: (_task_priority(t), _task_duration(t), int(t.get("id") or 0)))
        best = untimed[0]
        return f"W Twoim kontekście najlepiej pasuje: {_task_title(best)} (~{_task_duration(best)} min, p{_task_priority(best)})."

    best = timed[0]
    due = _task_due_min(best)
    delta = max(0, (due or now_min) - now_min)
    return f"Najbliższy kontekstowy krok: {_task_title(best)} (start za {_fmt_min(delta)})."


def quick_options(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    state = _load_state()
    if not tasks:
        return "Nie widzę dziś zadań do szybkiego wyboru."
    available = None
    try:
        if state.get("available_minutes") is not None:
            available = int(state["available_minutes"])
    except Exception:
        available = None

    untimed = [t for t in tasks if _task_due_min(t) is None]
    pool = untimed if untimed else tasks
    if available is not None:
        pool = [t for t in pool if _task_duration(t) <= available] or pool

    pool = sorted(pool, key=lambda t: (_task_priority(t), _task_duration(t), int(t.get("id") or 0)))[:3]
    lines = ["Kontekstowe opcje:", ""]
    for t in pool:
        lines.append(f"• {_task_title(t)} (~{_task_duration(t)} min, p{_task_priority(t)})")
    return "\n".join(lines)
