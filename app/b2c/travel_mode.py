from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from . import tasks as tasks_mod


DEFAULT_TRAVEL_MIN = 25
DEFAULT_BUFFER_MIN = 10

MODE_MINS = {
    "car": 25,
    "transit": 40,
    "bike": 18,
    "walk": 60,
}


def _fast_test_enabled() -> bool:
    """If enabled, travel and buffers are shortened so you can verify reminders quickly."""
    return os.environ.get("JARVIS_FAST_TEST", "").strip() in ("1", "true", "TRUE", "yes", "YES")


def _mode_minutes(mode: str) -> int:
    """Normal mode uses MODE_MINS. Fast-test mode forces 1 minute for every mode."""
    if _fast_test_enabled():
        return 1
    return MODE_MINS.get(mode, DEFAULT_TRAVEL_MIN)

def _parse_due(dt_str: str) -> Optional[datetime]:
    """Parse due datetime in a timezone-safe way.

    Accepts:
    - naive local ISO (YYYY-MM-DDTHH:MM)
    - ISO with offset (YYYY-MM-DDTHH:MM+01:00)
    - ISO UTC with trailing Z (YYYY-MM-DDTHH:MMZ)

    Returns a timezone-aware datetime converted to the *local* timezone.
    This avoids 1h offset confusion and prevents "naive vs aware" comparison errors.
    """
    if not dt_str or "T" not in dt_str:
        return None

    local_tz = datetime.now().astimezone().tzinfo
    raw = dt_str.replace("Z", "+00:00")

    dt: Optional[datetime] = None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        try:
            dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
        except Exception:
            return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=local_tz)
    return dt.astimezone(local_tz)

def _fmt_task_line(t: Dict[str, Any]) -> str:
    title = (t.get("title") or "(bez tytułu)").strip()
    loc = (t.get("location") or "").strip()
    due = t.get("due_at") or ""
    time = ""
    due_dt = _parse_due(due)
    if due_dt is not None:
        time = due_dt.strftime("%H:%M")
    suffix = f", {loc}" if loc else ""
    return f"• {time:>5} — {title}{suffix}" if time else f"• {title}{suffix}"

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

def morning_overview(*, buffer_min: int = DEFAULT_BUFFER_MIN) -> Dict[str, str]:
    today = date.today()
    tasks = tasks_mod.list_tasks_for_date(today)
    now = datetime.now().astimezone()

    # --- Inteligencja dnia (v1): sortujemy po priorytecie i godzinie ---
    def sort_key(t: Dict[str, Any]):
        pr_raw = t.get("priority", 2)
        try:
            pr = int(pr_raw)
        except Exception:
            m = re.match(r"^p\s*([1-5])$", str(pr_raw).strip().lower())
            pr = int(m.group(1)) if m else 2
        dt = _parse_due(t.get("due_at") or "")
        ts = dt.timestamp() if dt else 10**18
        return (pr, ts)

    tasks = sorted(tasks, key=sort_key)

    lines: List[str] = []
    lines.append("Dzień dobry 🙂 Sprawdźmy spokojnie, co dziś jest najważniejsze.")
    lines.append("")
    lines.append("**Najważniejsze dziś:**")

    if not tasks:
        lines.append("• Brak zaplanowanych zadań na dziś.")
        return {"reply": "\n".join(lines)}

    for t in tasks[:10]:
        line = _fmt_task_line(t)
        # keep list compact (without [P1]/[P2])
        line = re.sub(r"^\[[A-Z0-9]+\]\s*", "", line)
        lines.append(line)

    # Fokus dnia = pierwsza rzecz po sortowaniu
    if tasks:
        focus = tasks[0]
        pr_raw = focus.get("priority", 2)
        try:
            pr = int(pr_raw)
        except Exception:
            m = re.match(r"^p\s*([1-5])$", str(pr_raw).strip().lower())
            pr = int(m.group(1)) if m else 2
        pr_txt = {1: "wysoki", 2: "normalny", 3: "niski"}.get(pr, "normalny")
        dur = focus.get("duration_min")
        dur_txt = f" (~{dur} min)" if isinstance(dur, int) and dur > 0 else ""
        lines.append("")
        lines.append(f"🎯 **Fokus dnia** ({pr_txt}{dur_txt}): {focus.get('title','')}")
        lines.append("🧠 Propozycja: zrób to jako pierwsze, zanim wpadną nowe tematy.")

    next_task = _pick_next_task(tasks, now)
    if not next_task:
        lines.append("")
        lines.append("✅ Wygląda na to, że nie masz już dziś zadań z konkretną godziną.")
        return {"reply": "\n".join(lines)}

    due_dt = _parse_due(next_task.get("due_at") or "")
    if not due_dt:
        return {"reply": "\n".join(lines)}

    travel_mode = next_task.get("travel_mode")
    if not travel_mode:
        tasks_mod.set_pending_travel(int(next_task["id"]), created_from="rano")
        lines.append("")
        lines.append("Zaczynamy od pierwszego kroku: **ustalamy sposób dojazdu na pierwsze zadanie**.")
        lines.append("Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
        return {"reply": "\n".join(lines)}

    if _fast_test_enabled():
        buffer_min = 0
    travel_min = _mode_minutes(str(travel_mode))
    depart_at = due_dt - timedelta(minutes=(travel_min + buffer_min))

    lines.append("")
    lines.append("**Propozycja wyjścia:**")
    lines.append(
        f"Na pierwsze zadanie zakładam: **{travel_mode}** (~{travel_min} min) + {buffer_min} min zapasu → wyjście o **{depart_at:%H:%M}**."
    )

    reminder_at = depart_at.strftime("%Y-%m-%dT%H:%M")
    tasks_mod.set_pending_reminder(int(next_task["id"]), reminder_at, created_from="rano")
    lines.append("")
    lines.append(f"Ustawić przypomnienie na **{depart_at:%H:%M}**? (tak/nie)")

    lines.append("")
    lines.append("**CheckListy:**")
    lines.append("□ dokumenty / karta")
    lines.append("□ telefon")
    lines.append("□ wyjście z zapasem czasu")

    return {"reply": "\n".join(lines)}

def morning_brief() -> Dict[str, str]:
    return morning_overview()
