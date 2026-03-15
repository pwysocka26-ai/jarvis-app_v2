
from __future__ import annotations

import json
from pathlib import Path
from datetime import date
from typing import Any, Dict, List, Optional

LEARNING_FILE = Path("data/memory/learning_brain.json")


def _load_learning() -> Dict[str, Any]:
    if not LEARNING_FILE.exists():
        return {"sessions": [], "stats": {}}
    try:
        data = json.loads(LEARNING_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"sessions": [], "stats": {}}


def _today_tasks(tasks_mod) -> List[Dict[str, Any]]:
    try:
        tasks = tasks_mod.list_tasks_for_date(date.today()) or []
    except Exception:
        tasks = []
    return [t for t in tasks if isinstance(t, dict) and not bool(t.get("done"))]


def _title(task: Dict[str, Any]) -> str:
    title = str(task.get("title") or task.get("text") or "").strip()
    if title.lower().startswith("bez godziny "):
        title = title[len("bez godziny "):].strip()
    return title or "(bez tytułu)"


def _priority(task: Dict[str, Any]) -> int:
    try:
        return int(task.get("priority") or 2)
    except Exception:
        return 2


def _duration(task: Dict[str, Any]) -> int:
    try:
        return max(5, int(task.get("duration_min") or 30))
    except Exception:
        return 30


def _due_min(task: Dict[str, Any]) -> Optional[int]:
    due = str(task.get("due_at") or "")
    if "T" not in due:
        return None
    try:
        hhmm = due.split("T", 1)[1][:5]
        hh, mm = hhmm.split(":")
        return int(hh) * 60 + int(mm)
    except Exception:
        return None


def self_optimizing_brain(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    learning = _load_learning()
    stats = learning.get("stats", {}) if isinstance(learning, dict) else {}

    if not tasks:
        return "SELF-OPTIMIZING BRAIN\n\nNie masz dziś aktywnych zadań do optymalizacji."

    lines = ["SELF-OPTIMIZING BRAIN", ""]
    suggestions: List[str] = []

    for t in tasks:
        title = _title(t)
        st = stats.get(title.lower(), {})
        count = int(st.get("count", 0)) if isinstance(st, dict) else 0
        if count <= 0:
            continue
        avg = round(int(st.get("total_actual_min", 0)) / count) if count else _duration(t)
        planned = _duration(t)
        if avg > planned + 10:
            suggestions.append(f"• {title}: zwykle trwa ok. {avg} min, a planujesz {planned} min — zwiększ estymację.")
        if int(st.get("completed_count", 0)) < count and count >= 3:
            ratio = round((int(st.get("completed_count", 0)) / count) * 100)
            suggestions.append(f"• {title}: kończysz tylko w {ratio}% przypadków — rozbij to na mniejsze kroki albo obniż priorytet.")

    untimed = [t for t in tasks if _due_min(t) is None]
    timed = [t for t in tasks if _due_min(t) is not None]
    if untimed and timed:
        suggestions.append("• Masz miks zadań z godziną i bez godziny — wrzucaj elastyczne zadania między stałe punkty, nie przed najwcześniejszym blokiem dnia.")

    if not suggestions:
        suggestions.append("• Plan wygląda stabilnie. Kontynuuj fokus i zbieraj dane — Jarvis będzie optymalizował go coraz lepiej.")

    lines.append("Sugestie optymalizacji:")
    lines.extend(suggestions[:8])
    return "\n".join(lines)


def adaptive_plan(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    learning = _load_learning()
    stats = learning.get("stats", {}) if isinstance(learning, dict) else {}

    if not tasks:
        return "ADAPTIVE PLAN\n\nNie masz dziś aktywnych zadań."

    def score(task: Dict[str, Any]):
        title = _title(task)
        st = stats.get(title.lower(), {})
        count = int(st.get("count", 0)) if isinstance(st, dict) else 0
        avg = round(int(st.get("total_actual_min", 0)) / count) if count else _duration(task)
        completion = (int(st.get("completed_count", 0)) / count) if count else 0.5
        due = _due_min(task)
        return (0 if due is not None else 1, _priority(task), -completion, avg, int(task.get("id") or 0))

    ordered = sorted(tasks, key=score)

    lines = [f"ADAPTIVE PLAN — {date.today().isoformat()}", "", "Kolejność po optymalizacji:"]
    for idx, t in enumerate(ordered[:8], start=1):
        title = _title(t)
        st = stats.get(title.lower(), {})
        count = int(st.get("count", 0)) if isinstance(st, dict) else 0
        avg = round(int(st.get("total_actual_min", 0)) / count) if count else _duration(t)
        due = _due_min(t)
        if due is not None:
            hh = due // 60
            mm = due % 60
            lines.append(f"{idx}. {hh:02d}:{mm:02d} — {title} (realnie ~{avg} min)")
        else:
            lines.append(f"{idx}. {title} (realnie ~{avg} min)")
    return "\n".join(lines)
