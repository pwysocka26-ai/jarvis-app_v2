from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.b2c.maps_google import get_eta_minutes


def _today_iso() -> str:
    return date.today().isoformat()


def _task_title(task: Dict[str, Any]) -> str:
    return str(task.get("title") or task.get("text") or f"Zadanie #{task.get('id', '?')}").strip()


def _task_location(task: Dict[str, Any]) -> Optional[str]:
    for key in ("location", "location_text", "place", "address"):
        val = task.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _task_due_hhmm(task: Dict[str, Any]) -> Optional[str]:
    due_at = str(task.get("due_at") or "")
    if "T" in due_at and len(due_at) >= 16:
        return due_at.split("T", 1)[1][:5]
    time_v = task.get("time")
    if isinstance(time_v, str) and time_v.strip():
        return time_v.strip()[:5]
    return None


def _parse_hhmm(hhmm: Optional[str]) -> Optional[int]:
    if not hhmm or ":" not in hhmm:
        return None
    try:
        hh, mm = hhmm.split(":", 1)
        h, m = int(hh), int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h * 60 + m
    except Exception:
        return None
    return None


def _fmt_hhmm(total_min: int) -> str:
    total_min = max(0, min(23 * 60 + 59, int(total_min)))
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def _priority(task: Dict[str, Any]) -> int:
    try:
        return int(task.get("priority") or 2)
    except Exception:
        return 2


def _duration_min(task: Dict[str, Any]) -> int:
    v = task.get("duration_min")
    if isinstance(v, int) and v > 0:
        return v
    checklist = task.get("checklist")
    if isinstance(checklist, dict):
        items = checklist.get("items")
        if isinstance(items, list) and items:
            return max(20, min(90, len(items) * 10))
    return 30


def _maps_mode(mode: Optional[str]) -> str:
    low = (mode or "").strip().lower()
    mapping = {
        "samochod": "driving", "samochód": "driving", "samochodem": "driving", "driving": "driving", "car": "driving",
        "autobus": "transit", "komunikacja": "transit", "komunikacją": "transit", "transit": "transit",
        "rower": "bicycling", "rowerem": "bicycling", "bicycling": "bicycling", "bike": "bicycling",
        "pieszo": "walking", "walking": "walking", "walk": "walking",
    }
    return mapping.get(low, "driving")


def _display_mode(mode: Optional[str]) -> str:
    low = (mode or "").strip().lower()
    mapping = {
        "samochod": "samochodem", "samochód": "samochodem", "samochodem": "samochodem", "driving": "samochodem", "car": "samochodem",
        "autobus": "komunikacją", "komunikacja": "komunikacją", "komunikacją": "komunikacją", "transit": "komunikacją",
        "rower": "rowerem", "rowerem": "rowerem", "bicycling": "rowerem", "bike": "rowerem",
        "pieszo": "pieszo", "walking": "pieszo", "walk": "pieszo",
    }
    return mapping.get(low, "samochodem")


def _fallback_eta(mode: Optional[str]) -> int:
    low = (mode or "").strip().lower()
    if low in {"autobus", "komunikacja", "komunikacją", "transit"}:
        return 40
    if low in {"rower", "rowerem", "bike", "bicycling"}:
        return 18
    if low in {"pieszo", "walking", "walk"}:
        return 60
    return 25


def _eta_minutes(origin: Optional[str], destination: Optional[str], mode: Optional[str]) -> int:
    if not origin or not destination:
        return 0
    try:
        mins = get_eta_minutes(origin, destination, _maps_mode(mode))
        if isinstance(mins, int) and mins > 0:
            return mins
    except Exception:
        pass
    return _fallback_eta(mode)


def _today_tasks(tasks_mod) -> List[Dict[str, Any]]:
    return tasks_mod.sort_for_list(tasks_mod.list_tasks_for_date(_today_iso()) or [], mode="time")


def _timed_tasks(tasks: List[Dict[str, Any]]) -> List[Tuple[int, Dict[str, Any]]]:
    out: List[Tuple[int, Dict[str, Any]]] = []
    for t in tasks:
        mins = _parse_hhmm(_task_due_hhmm(t))
        if mins is not None:
            out.append((mins, t))
    out.sort(key=lambda x: (x[0], _priority(x[1]), int(x[1].get("id") or 0)))
    return out


def _untimed_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [t for t in tasks if _parse_hhmm(_task_due_hhmm(t)) is None]


def _free_windows(timed: List[Tuple[int, Dict[str, Any]]], day_end: int = 21 * 60) -> List[Tuple[int, int]]:
    windows: List[Tuple[int, int]] = []
    if not timed:
        return []
    for idx in range(len(timed) - 1):
        cur_start, cur_task = timed[idx]
        next_start, _next_task = timed[idx + 1]
        cur_end = cur_start + _duration_min(cur_task)
        if next_start - cur_end >= 20:
            windows.append((cur_end, next_start))
    last_start, last_task = timed[-1]
    last_end = last_start + _duration_min(last_task)
    if day_end - last_end >= 20:
        windows.append((last_end, day_end))
    return windows


def assess_all_today_schedule(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = 10) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    if not timed:
        return "Na dziś nie mam wielu twardych punktów z godziną, więc nie widzę ryzyka spóźnienia."

    mode = default_mode or "samochod"
    lines = [f"Ocena dnia — {_today_iso()}", ""]
    feasible = True
    prev_ready = None
    prev_loc = origin
    risks: List[str] = []
    for idx, (start_min, task) in enumerate(timed, start=1):
        title = _task_title(task)
        loc = _task_location(task)
        due = _fmt_hhmm(start_min)
        eta = 0
        travel_from = prev_loc if prev_loc else origin
        if loc and travel_from and (idx == 1 or prev_loc):
            eta = _eta_minutes(travel_from, loc, task.get("travel_mode") or default_mode)
        leave_min = start_min - eta - buffer_min if eta else start_min
        duration = _duration_min(task)
        lines.append(f"{idx}. {due} — {title}")
        if loc:
            lines.append(f"   miejsce: {loc}")
        if eta:
            lines.append(f"   wyjście: {_fmt_hhmm(leave_min)} • ETA: {eta} min • tryb: {_display_mode(task.get('travel_mode') or default_mode)}")
        if prev_ready is not None and leave_min < prev_ready:
            feasible = False
            risks.append(f"Konflikt: `{title}` wymaga wyjścia o {_fmt_hhmm(leave_min)}, a poprzedni blok kończy się około {_fmt_hhmm(prev_ready)}.")
        prev_ready = start_min + duration
        prev_loc = loc or prev_loc

    if feasible:
        lines.extend(["", "✅ Wygląda na to, że przy obecnym planie powinnaś zdążyć na wszystkie zadania."])
    else:
        lines.extend(["", "⚠️ Widzę ryzyka w planie dnia:"])
        for r in risks[:5]:
            lines.append(f"• {r}")
        lines.append("Spróbuj: `przełóż mniej ważne zadania` albo `zaplanuj mi dzień automatycznie`.")
    return "\n".join(lines)


def suggest_for_free_time(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    if not timed and not untimed:
        return "Na dziś nie masz jeszcze żadnych zadań."
    if not timed:
        if untimed:
            lines = ["Masz dziś elastyczny czas. Możesz zrobić teraz:"]
            for t in untimed[:3]:
                lines.append(f"• {_task_title(t)} (p{_priority(t)})")
            return "\n".join(lines)
        return "Nie widzę dziś wolnych okien, bo nie mam jeszcze zadań z godziną."

    free = _free_windows(timed)
    if not free:
        return "Dziś nie widzę większego wolnego okna między zadaniami."

    biggest = max(free, key=lambda w: w[1] - w[0])
    gap = biggest[1] - biggest[0]
    lines = [f"Największe wolne okno dziś: **{_fmt_hhmm(biggest[0])}–{_fmt_hhmm(biggest[1])}** ({gap} min)."]
    if untimed:
        fit = [t for t in untimed if _duration_min(t) <= gap + 10]
        if fit:
            lines.append("")
            lines.append("W tym czasie możesz zrobić:")
            for t in fit[:3]:
                lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
        else:
            lines.append("Nie widzę dziś zadania bez godziny, które dobrze mieści się w tym oknie.")
    else:
        lines.append("Nie masz dziś zadań bez godziny, więc to dobre miejsce na odpoczynek albo szybkie sprawy z inboxa.")
    return "\n".join(lines)


def postpone_lower_priority_tasks(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    if len(timed) < 2:
        return "Nie widzę dziś konfliktów wymagających przenoszenia zadań."

    moved: List[str] = []
    moved_ids = set()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    for idx in range(len(timed) - 1):
        start_a, a = timed[idx]
        start_b, b = timed[idx + 1]
        end_a = start_a + _duration_min(a)
        if start_b < end_a:
            pa, pb = _priority(a), _priority(b)
            candidate = b if pb >= pa else a
            if _priority(candidate) == 1:
                continue
            cid = int(candidate.get("id") or 0)
            if cid in moved_ids:
                continue
            hhmm = _task_due_hhmm(candidate) or "09:00"
            updated = tasks_mod.update_task(cid, due_at=f"{tomorrow}T{hhmm}") if hasattr(tasks_mod, 'update_task') else None
            if updated:
                moved_ids.add(cid)
                moved.append(f"• {_task_title(candidate)} → jutro {hhmm}")

    if not moved:
        return "Nie widzę dziś konfliktów, w których warto automatycznie przenosić mniej ważne zadania."
    return "Przełożyłam mniej ważne zadania:\n" + "\n".join(moved)


def auto_plan_day(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = 10) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    if not timed and not untimed:
        return "Na dziś nie masz jeszcze żadnych zadań."

    lines = [f"AUTOPLAN — {_today_iso()}", ""]
    if timed:
        lines.append("Stałe punkty dnia:")
        for start_min, t in timed:
            row = f"• {_fmt_hhmm(start_min)} {_task_title(t)}"
            loc = _task_location(t)
            if loc:
                row += f" — {loc}"
            lines.append(row)
    else:
        lines.append("Nie masz dziś jeszcze stałych punktów z godziną.")

    if untimed:
        windows = _free_windows(timed) if timed else [(9 * 60, 18 * 60)]
        proposed: List[str] = []
        remaining = untimed[:]
        for start_w, end_w in windows:
            cur = start_w
            idx = 0
            while idx < len(remaining):
                t = remaining[idx]
                dur = _duration_min(t)
                if cur + dur <= end_w:
                    proposed.append(f"• {_fmt_hhmm(cur)} {_task_title(t)} (~{dur} min, p{_priority(t)})")
                    cur += dur + 5
                    remaining.pop(idx)
                else:
                    idx += 1
        if proposed:
            lines.extend(["", "Proponuję wypełnić wolne okna tak:"])
            lines.extend(proposed)
        if remaining:
            lines.extend(["", "Na później zostawiłabym:"])
            for t in remaining[:5]:
                lines.append(f"• {_task_title(t)} (p{_priority(t)})")
    else:
        lines.extend(["", "Nie masz dziś zadań bez godziny — plan jest już dość czysty."])

    if timed:
        lines.extend(["", assess_all_today_schedule(tasks_mod, origin, default_mode, buffer_min=buffer_min)])
    return "\n".join(lines)
