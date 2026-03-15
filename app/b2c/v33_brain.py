
from __future__ import annotations

import json
from pathlib import Path
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

PERSONAL_MEMORY_FILE = Path("data/memory/personal_memory.json")
CONTEXT_FILE = Path("data/memory/context_brain.json")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return default


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


def _next_timed_task(tasks: List[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], int]]:
    now_min = _now_min()
    timed = []
    for t in tasks:
        due = _due_min(t)
        if due is not None and due >= now_min:
            timed.append((t, due - now_min))
    timed.sort(key=lambda x: x[1])
    return timed[0] if timed else None


def _today_timed_overview(tasks: List[Dict[str, Any]]) -> Tuple[int, int]:
    now_min = _now_min()
    timed_due = [d for d in (_due_min(t) for t in tasks) if d is not None]
    total = len(timed_due)
    future = len([d for d in timed_due if d >= now_min])
    return total, future


def _largest_gap(tasks: List[Dict[str, Any]]) -> Optional[int]:
    now_min = _now_min()
    due_times = sorted([d for d in (_due_min(t) for t in tasks) if d is not None and d >= now_min])
    if not due_times:
        return 180
    first_gap = due_times[0] - now_min
    return max(first_gap, 0)


def _personal_preferences() -> List[str]:
    data = _load_json(PERSONAL_MEMORY_FILE, {"facts": []})
    facts = [str(x).strip().lower() for x in data.get("facts", []) if str(x).strip()]
    prefs = []
    if any("lubię pracować rano" in f or "lubie pracowac rano" in f or "najlepiej pracuję rano" in f or "najlepiej pracuje rano" in f for f in facts):
        prefs.append("rano")
    if any("rano mam mało energii" in f or "rano mam malo energii" in f for f in facts):
        prefs.append("light_morning")
    return prefs


def _context_state() -> Dict[str, Any]:
    data = _load_json(CONTEXT_FILE, {})
    return data if isinstance(data, dict) else {}


def autonomous_brain(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    prefs = _personal_preferences()
    ctx = _context_state()

    lines = ["AUTONOMOUS BRAIN", ""]

    if not tasks:
        lines.append("Nie widzę dziś aktywnych zadań.")
        lines.append("Mogę zaproponować: dodaj zadanie, przejrzyj inbox albo zaplanuj jutro.")
        return "\n".join(lines)

    next_timed = _next_timed_task(tasks)
    gap = _largest_gap(tasks)
    timed_total, timed_future = _today_timed_overview(tasks)

    if next_timed:
        t, delta = next_timed
        lines.append(f"Najbliższy punkt: {_title(t)} za {_fmt_min(delta)}.")
    elif timed_total > 0:
        lines.append(f"Masz dziś {timed_total} zadanie(a) z konkretną godziną, ale nie ma już kolejnych przyszłych punktów.")
    else:
        lines.append("Nie masz dziś zadań z konkretną godziną.")

    if ctx.get("available_minutes"):
        lines.append(f"Dostępny czas w kontekście: {_fmt_min(int(ctx['available_minutes']))}.")

    untimed = [t for t in tasks if _due_min(t) is None]
    if untimed:
        untimed = sorted(untimed, key=lambda t: (_priority(t), _duration(t), int(t.get("id") or 0)))
        best = untimed[0]
        lines.extend(["", "Proaktywna sugestia:"])
        if gap is not None and gap >= _duration(best):
            lines.append(f"• Zrób teraz: {_title(best)} (~{_duration(best)} min, p{_priority(best)}).")
        else:
            lines.append(f"• Zachowaj na później: {_title(best)} (~{_duration(best)} min, p{_priority(best)}).")
    else:
        lines.extend(["", "Proaktywna sugestia:", "• Plan jest czysty — skup się na najbliższym stałym punkcie."])

    if "rano" in prefs:
        lines.append("• Pamiętam, że najlepiej pracujesz rano — najważniejsze bloki ustawiaj na rano.")
    if "light_morning" in prefs:
        lines.append("• Pamiętam, że rano masz mniej energii — zacznij od lżejszych zadań.")

    return "\n".join(lines)


def proactive_prompt(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    if not tasks:
        return "Autonomicznie: nie widzę dziś aktywnych zadań. Dodaj coś albo zamknij dzień."

    next_timed = _next_timed_task(tasks)
    untimed = [t for t in tasks if _due_min(t) is None]
    timed_total, timed_future = _today_timed_overview(tasks)
    if next_timed:
        task, delta = next_timed
        if 0 <= delta <= 15:
            return f"Autonomicznie: za {_fmt_min(delta)} zaczyna się {_title(task)}."
    elif timed_total > 0 and timed_future == 0:
        if untimed:
            untimed = sorted(untimed, key=lambda t: (_priority(t), _duration(t), int(t.get("id") or 0)))
            best = untimed[0]
            return f"Autonomicznie: dzisiejsze stałe punkty są już za Tobą, więc możesz domknąć {_title(best)} (~{_duration(best)} min)."
        return "Autonomicznie: dzisiejsze stałe punkty są już za Tobą. Możesz zamknąć dzień albo zaplanować jutro."
    if untimed:
        untimed = sorted(untimed, key=lambda t: (_priority(t), _duration(t), int(t.get("id") or 0)))
        best = untimed[0]
        return f"Autonomicznie: masz przestrzeń na {_title(best)} (~{_duration(best)} min)."
    return "Autonomicznie: plan wygląda stabilnie."
