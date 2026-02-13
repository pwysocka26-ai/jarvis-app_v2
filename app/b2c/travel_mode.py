from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from . import tasks as tasks_mod
from .tasks import list_tasks_for_date


# --- Product MVP: Morning brief (light state: pending travel + reminder) ------
# Triggered by user message "rano" (router handles this)
# - Prints today's key tasks
# - For the first upcoming task:
#   * if travel mode missing -> ask user and save pending_travel
#   * else -> suggest departure time and ask whether to set a reminder (pending_reminder)


DEFAULT_TRAVEL_MIN = 30
DEFAULT_BUFFER_MIN = 30

MODE_MINS = {
    "samochodem": 25,
    "komunikacją": 40,
    "rowerem": 35,
    "pieszo": 60,
}


def _parse_due(due_at: str) -> Optional[datetime]:
    due_at = (due_at or "").strip()
    if not due_at:
        return None
    # Accept "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"
    try:
        if "T" in due_at:
            return datetime.fromisoformat(due_at)
        return datetime.fromisoformat(due_at + "T00:00")
    except Exception:
        return None


def _pick_next_task(tasks: List[Dict[str, Any]], now: datetime) -> Optional[Dict[str, Any]]:
    best = None
    best_dt = None
    for t in tasks:
        dt = _parse_due(t.get("due_at") or "")
        if not dt:
            continue
        if dt < now:
            continue
        if best_dt is None or dt < best_dt:
            best = t
            best_dt = dt
    return best


def _fmt_task_line(t: Dict[str, Any]) -> str:
    title = (t.get("title") or "(bez tytułu)").strip()
    loc = (t.get("location") or "").strip()
    due = (t.get("due_at") or "").strip()

    time = ""
    if "T" in due:
        time = due.split("T", 1)[1][:5]

    suffix = f", {loc}" if loc else ""
    if time:
        return f"• {time:>5} — {title}{suffix}"
    return f"• {title}{suffix}"


def morning_overview(*, buffer_min: int = DEFAULT_BUFFER_MIN) -> Dict[str, str]:
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

    for t in tasks[:10]:
        lines.append(_fmt_task_line(t))

    next_task = _pick_next_task(tasks, now)
    if not next_task:
        lines.append("")
        lines.append("✅ Wygląda na to, że nie masz już dziś zadań z konkretną godziną.")
        return {"reply": "\n".join(lines)}

    due_dt = _parse_due(next_task.get("due_at") or "")
    if not due_dt:
        return {"reply": "\n".join(lines)}

    travel_mode = (next_task.get("travel_mode") or "").strip().lower() or None
    if not travel_mode:
        tasks_mod.set_pending_travel(int(next_task["id"]), created_from="rano")
        lines.append("")
        lines.append("Zaczynamy od pierwszego kroku: **ustalamy sposób dojazdu na pierwsze zadanie**.")
        lines.append("Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
        return {"reply": "\n".join(lines)}

    travel_min = MODE_MINS.get(travel_mode, DEFAULT_TRAVEL_MIN)
    depart_at = due_dt - timedelta(minutes=(travel_min + buffer_min))

    lines.append("")
    lines.append("**Propozycja wyjścia:**")
    lines.append(
        f"Na pierwsze zadanie zakładam: **{travel_mode}** (~{travel_min} min) + {buffer_min} min zapasu → wyjście o **{depart_at:%H:%M}**."
    )

    # ask about reminder
    reminder_at = depart_at.strftime("%Y-%m-%dT%H:%M")
    tasks_mod.set_pending_reminder(int(next_task["id"]), reminder_at, created_from="rano")
    lines.append("")
    lines.append(f"Ustawić przypomnienie na **{depart_at:%H:%M}**? (tak/nie)")

    # checklist
    lines.append("")
    lines.append("**CheckListy:**")
    lines.append("□ dokumenty / karta")
    lines.append("□ telefon")
    lines.append("□ wyjście z zapasem czasu")

    return {"reply": "\n".join(lines)}


def morning_brief() -> Dict[str, str]:
    return morning_overview()
