from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, date
from typing import Any, Dict, List, Optional

STATE_FILE = Path("data/memory/focus_loop.json")


def _ensure_dir() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> Optional[Dict[str, Any]]:
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _save_state(data: Dict[str, Any]) -> None:
    _ensure_dir()
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_state() -> None:
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except Exception:
        pass


def _today_tasks(tasks_mod) -> List[Dict[str, Any]]:
    try:
        tasks = tasks_mod.list_tasks_for_date(date.today()) or []
    except Exception:
        tasks = []
    return [t for t in tasks if isinstance(t, dict) and not bool(t.get("done"))]


def _priority(task: Dict[str, Any]) -> int:
    try:
        return int(task.get("priority") or 2)
    except Exception:
        return 2


def _duration(task: Dict[str, Any]) -> int:
    try:
        d = int(task.get("duration_min") or 30)
        return max(5, d)
    except Exception:
        return 30


def _title(task_or_state: Dict[str, Any]) -> str:
    title = str(task_or_state.get("title") or task_or_state.get("text") or "").strip()
    if title.lower().startswith("bez godziny "):
        title = title[len("bez godziny "):].strip()
    return title or "(bez tytułu)"


def _due_minutes(task: Dict[str, Any]) -> Optional[int]:
    due = str(task.get("due_at") or "")
    if "T" not in due:
        return None
    try:
        hhmm = due.split("T", 1)[1][:5]
        hh, mm = hhmm.split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return None


def _fmt_min(mins: int) -> str:
    h, m = divmod(max(0, mins), 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"


def _find_task_by_id(tasks_mod, task_id: int) -> Optional[Dict[str, Any]]:
    for t in _today_tasks(tasks_mod):
        if int(t.get("id") or -1) == int(task_id):
            return t
    return None


def _pick_focus_task(tasks_mod) -> Optional[Dict[str, Any]]:
    tasks = _today_tasks(tasks_mod)
    if not tasks:
        return None
    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    untimed = [t for t in tasks if _due_minutes(t) is None]
    timed = sorted([t for t in tasks if _due_minutes(t) is not None], key=lambda t: (_due_minutes(t) or 10**9, _priority(t), int(t.get("id") or 0)))

    for t in timed:
        due = _due_minutes(t)
        if due is not None and 0 <= due - now_min <= 20:
            return t

    if untimed:
        untimed = sorted(untimed, key=lambda t: (_priority(t), int(t.get("id") or 0)))
        return untimed[0]

    return timed[0] if timed else None


def start_focus(tasks_mod, explicit_task_id: Optional[int] = None) -> str:
    current = _load_state()
    if current and current.get("active"):
        return f"Masz już aktywny fokus: {_title(current)}. Użyj `ile zostało czasu`, `skończyłem` albo `anuluj fokus`."

    task = _find_task_by_id(tasks_mod, explicit_task_id) if explicit_task_id else _pick_focus_task(tasks_mod)
    if not task:
        return "Nie widzę teraz zadania, na którym warto uruchomić fokus."

    state = {
        "active": True,
        "task_id": int(task.get("id") or 0),
        "title": _title(task),
        "duration_min": _duration(task),
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_state(state)
    return (
        f"🎯 Start fokusu: {state['title']} ({state['duration_min']} min).\n"
        "Napisz `ile zostało czasu` żeby sprawdzić status albo `skończyłem`, gdy zakończysz."
    )


def focus_status() -> str:
    state = _load_state()
    if not state or not state.get("active"):
        return "Nie masz teraz aktywnego fokusu."
    started = datetime.fromisoformat(str(state.get("started_at")))
    elapsed = int((datetime.now() - started).total_seconds() // 60)
    duration = int(state.get("duration_min") or 30)
    remaining = max(0, duration - elapsed)
    return (
        f"⏱ Fokus trwa: {state.get('title')}\n"
        f"Minęło: {_fmt_min(elapsed)}\n"
        f"Zostało: {_fmt_min(remaining)}"
    )


def finish_focus(tasks_mod) -> str:
    state = _load_state()
    if not state or not state.get("active"):
        return "Nie masz teraz aktywnego fokusu."
    task_id = int(state.get("task_id") or 0)
    title = str(state.get("title") or "zadanie")
    try:
        if hasattr(tasks_mod, "update_task"):
            tasks_mod.update_task(task_id, done=True)
    except Exception:
        pass
    _clear_state()
    return f"✅ Zakończono fokus i oznaczono jako zrobione: {title}"


def cancel_focus() -> str:
    state = _load_state()
    if not state or not state.get("active"):
        return "Nie masz teraz aktywnego fokusu."
    title = str(state.get("title") or "zadanie")
    _clear_state()
    return f"🛑 Anulowano fokus: {title}"
