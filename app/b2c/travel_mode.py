from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .tasks import list_tasks_for_date


# --- Product MVP: Morning overview (NO dialog / NO state) --------------------
# Idea:
# - Triggered by user message "rano" (router handles this)
# - Prints today's key tasks
# - Computes a *suggested* departure time for the first upcoming task
# - Uses simple assumptions (can be improved later):
#     travel_time = 25 min, buffer = 10 min
# - Does NOT ask questions and does NOT wait for "samochodem/pieszo" etc.


DEFAULT_TRAVEL_MIN = 25
DEFAULT_BUFFER_MIN = 10


def _parse_due(dt_str: str) -> Optional[datetime]:
    """Parse ISO-like due_at (YYYY-MM-DDTHH:MM). Return None if missing/invalid."""
    if not dt_str or "T" not in dt_str:
        return None
    try:
        # Accept both HH:MM and HH:MM:SS
        return datetime.fromisoformat(dt_str)
    except ValueError:
        try:
            return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M")
        except Exception:
            return None


def _fmt_task_line(t: Dict[str, Any]) -> str:
    title = (t.get("title") or "(bez tytułu)").strip()
    due = t.get("due_at") or ""
    time = ""
    if "T" in due:
        time = due.split("T", 1)[1][:5]  # HH:MM
    return f"• {time:>5} — {title}" if time else f"• {title}"


def _pick_next_task(tasks: List[Dict[str, Any]], now: datetime) -> Optional[Dict[str, Any]]:
    upcoming: List[tuple[datetime, Dict[str, Any]]] = []
    for t in tasks:
        if t.get("done") is True:
            continue
        due_dt = _parse_due(t.get("due_at") or "")
        if due_dt is None:
            continue
        if due_dt >= now:
            upcoming.append((due_dt, t))
    if not upcoming:
        return None
    upcoming.sort(key=lambda x: x[0])
    return upcoming[0][1]


def morning_overview(*, travel_min: int = DEFAULT_TRAVEL_MIN, buffer_min: int = DEFAULT_BUFFER_MIN) -> Dict[str, str]:
    """Return a dict with 'reply' for CLI."""
    today = date.today()
    tasks = list_tasks_for_date(today.isoformat())

    now = datetime.now()
    lines: List[str] = []
    lines.append("Dzień dobry 🙂 Sprawdźmy spokojnie, co dziś jest najważniejsze.")
    lines.append("")
    lines.append("**Najważniejsze dziś:**")

    if not tasks:
        lines.append("• Brak zaplanowanych zadań na dziś.")
        return {"reply": "\n".join(lines)}

    # List tasks (already filtered to today by storage layer)
    for t in tasks[:10]:
        lines.append(_fmt_task_line(t))

    # Suggest departure time for the next upcoming task (if any)
    next_task = _pick_next_task(tasks, now)
    if next_task:
        due_dt = _parse_due(next_task.get("due_at") or "")
        assert due_dt is not None
        depart_at = due_dt - timedelta(minutes=(travel_min + buffer_min))
        mins_left = int((due_dt - now).total_seconds() // 60)

        lines.append("")
        lines.append("**Propozycja wyjścia:**")
        lines.append(
            f"Zakładam dojazd **samochodem**: ~{travel_min} min + {buffer_min} min zapasu → wyjście o **{depart_at:%H:%M}**."
        )

        # Simple warning when it's getting tight
        if mins_left <= (travel_min + buffer_min + 5):
            lines.append("")
            lines.append("⚠️ **Uwaga:** Masz mało czasu — to zadanie jest już blisko.")

    # Minimal checklist (product-y)
    lines.append("")
    lines.append("**CheckListy:**")
    lines.append("□ dokumenty / karta")
    lines.append("□ telefon")
    lines.append("□ wyjście z zapasem czasu")

    return {"reply": "\n".join(lines)}


# Backwards-compatible alias used by router

def morning_brief() -> Dict[str, str]:
    return morning_overview()
