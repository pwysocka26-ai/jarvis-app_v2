
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

DATA_DIR = Path("data/memory")

def _load_list(name: str) -> List[Any]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        return data["tasks"]
    return []

def _title(x: Any) -> str:
    if isinstance(x, dict):
        return str(x.get("title") or x.get("text") or "").strip()
    return str(x).strip()

def proactive_day_brief(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = 10) -> str:
    from app.b2c.context_ai import auto_plan_day, daily_next_step
    parts = [auto_plan_day(tasks_mod, origin, default_mode, buffer_min=buffer_min)]
    try:
        nxt = daily_next_step(tasks_mod, origin, default_mode, buffer_min=buffer_min)
        parts.extend(["", "Teraz / zaraz:", nxt])
    except Exception:
        pass
    return "\n".join(parts)

def leave_check(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = 10) -> str:
    from app.b2c.context_ai import prepare_for_next_task
    return prepare_for_next_task(tasks_mod, origin, default_mode, buffer_min=buffer_min)

def inbox_brain_next(tasks_mod=None) -> str:
    ideas = _load_list("ideas.json")
    notes = _load_list("notes.json")
    reminders = _load_list("reminders.json")
    if reminders:
        return "Najpierw przejrzyj reminders — to najszybsza droga do rzeczy pilnych."
    if ideas:
        return "Masz pomysły do doprecyzowania — wybierz 1 i zamień go w konkretne zadanie."
    if notes:
        return "Masz notatki — przejrzyj 1 najnowszą i zdecyduj: zadanie, pomysł albo archiwum."
    return "Nie widzę teraz nic pilnego w inboxie. Możesz dodać nowe informacje albo zaplanować dzień."

def inbox_brain_summary(tasks_mod=None) -> str:
    ideas = _load_list("ideas.json")
    notes = _load_list("notes.json")
    reminders = _load_list("reminders.json")
    tasks = _load_list("tasks.json")
    active_tasks = [t for t in tasks if isinstance(t, dict) and not t.get("done")]
    out = ["INBOX BRAIN", ""]
    out.append(f"Pomysły: {len(ideas)}")
    out.append(f"Notatki: {len(notes)}")
    out.append(f"Reminders: {len(reminders)}")
    out.append(f"Zadania: {len(active_tasks)}")
    previews = []
    if ideas:
        previews.append("Pomysły: " + "; ".join(_title(x) for x in ideas[:3] if _title(x)))
    if notes:
        previews.append("Notatki: " + "; ".join(_title(x) for x in notes[:3] if _title(x)))
    if reminders:
        previews.append("Reminders: " + "; ".join(_title(x) for x in reminders[:3] if _title(x)))
    if previews:
        out.extend(["", *previews])
    else:
        out.extend(["", "Inbox jest prawie pusty."])
    out.extend(["", inbox_brain_next(tasks_mod)])
    return "\n".join(out)
