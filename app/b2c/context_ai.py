from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.b2c.maps_google import get_eta_minutes

DAY_START_MIN = 6 * 60
DAY_END_MIN = 21 * 60
DEFAULT_BUFFER_MIN = 10
DEFAULT_TASK_DURATION_MIN = 30


def _today_iso() -> str:
    return date.today().isoformat()


def _now_min() -> int:
    now = datetime.now()
    return now.hour * 60 + now.minute


def _task_title(task: Dict[str, Any]) -> str:
    return str(task.get("title") or task.get("text") or f"Zadanie #{task.get('id', '?')}").strip()


def _task_location(task: Dict[str, Any]) -> Optional[str]:
    for key in ("location", "location_text", "place", "address"):
        val = task.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _task_due_hhmm(task: Dict[str, Any]) -> Optional[str]:
    due_at = task.get("due_at")
    if isinstance(due_at, str) and "T" in due_at and len(due_at) >= 16:
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
    return DEFAULT_TASK_DURATION_MIN


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


def _tomorrow_tasks(tasks_mod) -> List[Dict[str, Any]]:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    return tasks_mod.sort_for_list(tasks_mod.list_tasks_for_date(tomorrow) or [], mode="time")


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


def _free_windows(timed: List[Tuple[int, Dict[str, Any]]], day_start: int = DAY_START_MIN, day_end: int = DAY_END_MIN) -> List[Tuple[int, int]]:
    windows: List[Tuple[int, int]] = []
    if not timed:
        return [(day_start, day_end)] if day_end - day_start >= 20 else []

    first_start, _ = timed[0]
    if first_start - day_start >= 20:
        windows.append((day_start, first_start))

    for idx in range(len(timed) - 1):
        cur_start, cur_task = timed[idx]
        next_start, _ = timed[idx + 1]
        cur_end = cur_start + _duration_min(cur_task)
        if next_start - cur_end >= 20:
            windows.append((cur_end, next_start))

    last_start, last_task = timed[-1]
    last_end = last_start + _duration_min(last_task)
    if day_end - last_end >= 20:
        windows.append((last_end, day_end))
    return windows


def _windows_from_now(timed: List[Tuple[int, Dict[str, Any]]], now_min: Optional[int] = None, day_end: int = DAY_END_MIN) -> List[Tuple[int, int]]:
    if now_min is None:
        now_min = _now_min()
    prev = max(DAY_START_MIN, now_min)
    windows: List[Tuple[int, int]] = []
    for start_min, task in timed:
        end_min = start_min + _duration_min(task)
        if end_min <= prev:
            continue
        if start_min > prev and start_min - prev >= 5:
            windows.append((prev, start_min))
        prev = max(prev, end_min)
    if day_end - prev >= 5:
        windows.append((prev, day_end))
    return windows


def _largest_window(windows: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    return max(windows, key=lambda w: (w[1] - w[0], -w[0])) if windows else None


def _human_delta(target_min: int, now_min: int) -> str:
    delta = target_min - now_min
    if delta >= 0:
        h, m = divmod(delta, 60)
        if h and m:
            return f"za {h} h {m} min"
        if h:
            return f"za {h} h"
        return f"za {m} min"
    delta = abs(delta)
    h, m = divmod(delta, 60)
    if h and m:
        return f"{h} h {m} min temu"
    if h:
        return f"{h} h temu"
    return f"{m} min temu"


def _generic_suggestions() -> List[str]:
    return [
        "• zrób szybki przegląd inboxa",
        "• doprecyzuj 1 pomysł albo 1 notatkę",
        "• przygotuj rzeczy do następnego wyjścia",
    ]


def assess_all_today_schedule(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    if not timed:
        return "Na dziś nie mam wielu twardych punktów z godziną, więc nie widzę ryzyka spóźnienia."

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
        if loc and travel_from:
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
                lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
            return "\n".join(lines)
        return "Nie widzę dziś wolnych okien, bo nie mam jeszcze zadań z godziną."

    free = _free_windows(timed)
    if not free:
        return "Dziś nie widzę większego wolnego okna między zadaniami."

    biggest = _largest_window(free)
    if biggest is None:
        return "Dziś nie widzę większego wolnego okna między zadaniami."
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
        lines.extend(_generic_suggestions())
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


def auto_plan_day(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    if not timed and not untimed:
        return "Na dziś nie masz jeszcze żadnych zadań."

    now_min = _now_min()
    lines = [f"AUTOPLANER DNIA — {_today_iso()}", ""]
    if timed:
        lines.append("Stałe punkty dnia:")
        for start_min, t in timed:
            row = f"• {_fmt_hhmm(start_min)} {_task_title(t)}"
            loc = _task_location(t)
            if loc:
                row += f" — {loc}"
            lines.append(row)
    else:
        lines.append("Nie masz dziś stałych punktów z godziną.")

    windows_now = _windows_from_now(timed, now_min) if timed else ([(now_min, DAY_END_MIN)] if DAY_END_MIN - now_min >= 5 else [])
    proposed: List[str] = []
    remaining = untimed[:]
    for start_w, end_w in windows_now:
        cur = start_w
        idx = 0
        while idx < len(remaining):
            task = remaining[idx]
            dur = _duration_min(task)
            if cur + dur <= end_w:
                proposed.append(f"• {_fmt_hhmm(cur)} {_task_title(task)} (~{dur} min, p{_priority(task)})")
                cur += dur + 5
                remaining.pop(idx)
            else:
                idx += 1

    if proposed:
        lines.extend(["", "Proponowane wypełnienie wolnych okien:"])
        lines.extend(proposed)
    elif untimed:
        lines.extend(["", "Nie widzę już dziś sensownego miejsca, żeby wcisnąć elastyczne zadania od teraz."])

    all_windows = _free_windows(timed) if timed else [(max(now_min, DAY_START_MIN), DAY_END_MIN)]
    biggest = _largest_window(all_windows)
    if biggest:
        lines.extend(["", f"Największe wolne okno: {_fmt_hhmm(biggest[0])}–{_fmt_hhmm(biggest[1])} ({biggest[1]-biggest[0]} min)"])
    if remaining:
        lines.extend(["", "Na później zostawiłabym:"])
        for task in remaining[:5]:
            lines.append(f"• {_task_title(task)} (~{_duration_min(task)} min, p{_priority(task)})")

    lines.extend(["", "Sugestia:"])
    if proposed:
        lines.append("• Zacznij od pierwszego zaproponowanego elastycznego zadania i zostaw bufor 5–10 min między blokami.")
    elif untimed:
        lines.append("• Nie upychaj już nic na siłę. Zostaw elastyczne zadania na później albo jutro.")
    else:
        lines.append("• Plan wygląda lekko — możesz wykorzystać wolne okno na odpoczynek albo szybki przegląd inboxa.")
    return "\n".join(lines)


def suggest_now_with_limit(tasks_mod, minutes: int) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    now_min = _now_min()
    limit = max(5, int(minutes))

    windows = _windows_from_now(timed, now_min) if timed else ([(now_min, DAY_END_MIN)] if DAY_END_MIN - now_min >= 5 else [])
    usable = [w for w in windows if w[1] - w[0] >= limit]

    if not usable:
        all_windows = _free_windows(timed) if timed else [(max(now_min, DAY_START_MIN), DAY_END_MIN)]
        biggest = _largest_window(all_windows)
        if biggest is None:
            return f"Nie widzę już dziś wolnego okna na około {limit} min.\n" + "\n".join(_generic_suggestions())
        gap = biggest[1] - biggest[0]
        lines = [f"Największe dzisiejsze okno ma **{gap} min** ({_fmt_hhmm(biggest[0])}–{_fmt_hhmm(biggest[1])})."]
        fit = [t for t in untimed if _duration_min(t) <= min(limit, gap) + 5]
        if fit:
            lines.append(f"W oknie około {limit} min zmieści się:")
            for t in fit[:3]:
                lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
        else:
            lines.append(f"Nie widzę dziś zadania bez godziny, które dobrze mieści się w {limit} min.")
            lines.extend(_generic_suggestions())
        return "\n".join(lines)

    start_w, end_w = usable[0]
    fit = [t for t in untimed if _duration_min(t) <= limit + 5]
    lines = [f"Masz teraz okno **{_fmt_hhmm(start_w)}–{_fmt_hhmm(end_w)}**."]
    if fit:
        lines.extend(["", f"W {limit} min możesz zrobić:"])
        for t in fit[:3]:
            lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
    else:
        lines.extend(["", f"W tym oknie nie widzę zadania bez godziny, które dobrze mieści się w {limit} min."])
        lines.extend(_generic_suggestions())
    return "\n".join(lines)


def optimize_day_plan(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    if not timed and not untimed:
        return "Nie mam dziś nic do optymalizacji."

    lines = [f"OPTYMALIZACJA DNIA — {_today_iso()}", ""]
    if timed:
        lines.append("Stałe punkty:")
        for start_min, t in timed:
            lines.append(f"• {_fmt_hhmm(start_min)} {_task_title(t)}")
    conflicts: List[str] = []
    suggestions: List[str] = []
    for idx in range(len(timed) - 1):
        start_a, a = timed[idx]
        start_b, b = timed[idx + 1]
        end_a = start_a + _duration_min(a)
        if start_b < end_a:
            lo = b if _priority(b) >= _priority(a) else a
            conflicts.append(f"• konflikt: {_task_title(a)} ↔ {_task_title(b)}")
            suggestions.append(f"• rozważ przeniesienie: {_task_title(lo)} (p{_priority(lo)})")
    free = _free_windows(timed) if timed else []
    if free:
        biggest = _largest_window(free)
        if biggest:
            lines.extend(["", f"Największe wolne okno: {_fmt_hhmm(biggest[0])}–{_fmt_hhmm(biggest[1])} ({biggest[1]-biggest[0]} min)"])
            if untimed:
                fit = [t for t in untimed if _duration_min(t) <= (biggest[1]-biggest[0])]
                if fit:
                    lines.append("Warto tam wrzucić:")
                    for t in fit[:3]:
                        lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
            else:
                lines.append("Jeśli chcesz wykorzystać to okno lepiej, dodaj 1–2 małe zadania bez godziny albo zrób przegląd inboxa.")
    if conflicts:
        lines.extend(["", "Konflikty:"])
        lines.extend(conflicts)
    if suggestions:
        lines.extend(["", "Sugestie:"])
        lines.extend(suggestions)
    if not conflicts and not untimed:
        lines.extend(["", "Plan wygląda już dość optymalnie.", "Możesz wykorzystać największe okno na odpoczynek, inbox albo przygotowanie do kolejnego punktu."])
    elif not conflicts:
        lines.extend(["", "Nie widzę konfliktów. Skupiłabym się na wypełnieniu wolnych okien zadaniami bez godziny."])
    return "\n".join(lines)


def prepare_for_next_task(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    now_min = _now_min()

    upcoming = [(s, t) for s, t in timed if s >= now_min]
    if upcoming:
        start_min, task = upcoming[0]
        status = _human_delta(start_min, now_min)
    elif untimed:
        task = untimed[0]
        return (
            f"Najlepszy następny krok: **{_task_title(task)}** (~{_duration_min(task)} min, p{_priority(task)}).\n"
            "To dobre miejsce na małe elastyczne zadanie przed zamknięciem dnia."
        )
    elif timed:
        start_min, task = timed[-1]
        status = "to był ostatni dzisiejszy punkt"
    else:
        return "Nie widzę już dziś kolejnego zadania z godziną."

    title = _task_title(task)
    due = _fmt_hhmm(start_min)
    loc = _task_location(task)
    mode = task.get('travel_mode') or default_mode or 'samochod'
    eta = _eta_minutes(origin, loc, mode) if origin and loc else 0
    leave = start_min - eta - buffer_min if eta else None
    lines = [f"Następne zadanie: **{due} {title}**", f"Za: {status}"]
    if loc:
        lines.append(f"Miejsce: {loc}")
    if eta and leave is not None and status not in {"jutro", "to był ostatni dzisiejszy punkt"}:
        lines.append(f"Wyjdź około **{_fmt_hhmm(leave)}** • ETA: {eta} min • Tryb: {_display_mode(mode)}")

    checklist = task.get('checklist')
    if isinstance(checklist, dict) and isinstance(checklist.get('items'), list) and checklist['items']:
        lines.append("")
        lines.append("Sprawdź przed wyjściem:")
        for item in checklist['items'][:5]:
            if isinstance(item, dict):
                lines.append(f"• {item.get('text', '').strip()}")
            else:
                lines.append(f"• {str(item).strip()}")
    else:
        lines.append("")
        lines.append("Do tego czasu możesz:")
        lines.extend(_generic_suggestions()[:2])
    return "\n".join(lines)


def plan_whole_day(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    base = auto_plan_day(tasks_mod, origin, default_mode, buffer_min=buffer_min)
    extra = suggest_for_current_window(tasks_mod, origin, default_mode, buffer_min=buffer_min)
    return base + "\n\n" + extra


def _current_window(tasks_mod) -> Optional[Tuple[int, int]]:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    now_min = _now_min()
    windows = _windows_from_now(timed, now_min) if timed else ([(now_min, DAY_END_MIN)] if DAY_END_MIN - now_min >= 5 else [])
    return windows[0] if windows else None


def prepare_my_day(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    if not tasks:
        return "Na dziś nie masz jeszcze żadnych zadań. Dodaj 1–2 stałe punkty albo wrzuć coś do inboxa."

    lines = [f"PRZYGOTOWANIE DNIA — {_today_iso()}", ""]
    if timed:
        lines.append("Najważniejsze punkty dnia:")
        for start_min, task in timed[:5]:
            row = f"• {_fmt_hhmm(start_min)} {_task_title(task)}"
            loc = _task_location(task)
            if loc:
                row += f" — {loc}"
            lines.append(row)
    else:
        lines.append("Nie masz dziś jeszcze twardych punktów z godziną.")

    if untimed:
        lines.extend(["", "Elastyczne zadania, które możesz wcisnąć między punkty:"])
        for task in untimed[:3]:
            lines.append(f"• {_task_title(task)} (~{_duration_min(task)} min, p{_priority(task)})")

    free = _free_windows(timed) if timed else [(DAY_START_MIN, DAY_END_MIN)]
    biggest = _largest_window(free)
    if biggest:
        lines.extend(["", f"Największe wolne okno: {_fmt_hhmm(biggest[0])}–{_fmt_hhmm(biggest[1])} ({biggest[1]-biggest[0]} min)"])

    if timed:
        first_start, first_task = timed[0]
        loc = _task_location(first_task)
        mode = first_task.get('travel_mode') or default_mode or 'samochod'
        eta = _eta_minutes(origin, loc, mode) if origin and loc else 0
        leave = first_start - eta - buffer_min if eta else None
        lines.extend(["", f"Pierwszy punkt: {_fmt_hhmm(first_start)} {_task_title(first_task)}"])
        if loc:
            lines.append(f"Miejsce: {loc}")
        if eta and leave is not None:
            lines.append(f"Wyjdź około {_fmt_hhmm(leave)} • ETA: {eta} min • Tryb: {_display_mode(mode)}")

    lines.extend(["", "Sugestia:"])
    if untimed:
        lines.append("• Zacznij od twardych punktów, a potem wrzuć 1 małe zadanie bez godziny w największe wolne okno.")
    else:
        lines.append("• Jeśli plan wygląda lekko, dorzuć 1 małe zadanie bez godziny albo zrób szybki przegląd inboxa.")
    return "\n".join(lines)


def suggest_for_current_window(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    now_min = _now_min()
    timed = _timed_tasks(tasks)
    windows_now = _windows_from_now(timed, now_min)
    windows_day = _free_windows(timed) if timed else [(DAY_START_MIN, DAY_END_MIN)]

    active = windows_now[0] if windows_now else None
    lines: List[str] = []
    if active:
        start_w, end_w = active
        lines.append(f"Aktualne okno: **{_fmt_hhmm(start_w)}–{_fmt_hhmm(end_w)}** ({end_w-start_w} min).")
        gap = end_w - start_w
    else:
        biggest = _largest_window(windows_day)
        if not biggest:
            return "Nie widzę już dziś sensownego wolnego okna. Został tylko ostatni punkt albo dzień jest domknięty."
        start_w, end_w = biggest
        gap = end_w - start_w
        lines.append(f"Nie ma już aktywnego okna od teraz, ale największe dzisiejsze okno to **{_fmt_hhmm(start_w)}–{_fmt_hhmm(end_w)}** ({gap} min).")

    fit = [t for t in untimed if _duration_min(t) <= gap]
    if fit:
        lines.extend(["", "W to okno zmieści się:"])
        for task in fit[:4]:
            lines.append(f"• {_task_title(task)} (~{_duration_min(task)} min, p{_priority(task)})")
    else:
        lines.extend(["", "Nie masz dziś zadania bez godziny, które naturalnie wypełni to okno."])
        lines.extend(_generic_suggestions())
    return "\n".join(lines)


def daily_next_step(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    now_min = _now_min()

    for start_min, task in timed:
        title = _task_title(task)
        loc = _task_location(task)
        mode = task.get('travel_mode') or default_mode or 'samochod'
        eta = _eta_minutes(origin, loc, mode) if origin and loc else 0
        leave = start_min - eta - buffer_min if eta else start_min
        if now_min < leave:
            slack = leave - now_min
            if slack >= 20 and untimed:
                fit = [t for t in untimed if _duration_min(t) <= slack]
                if fit:
                    task_soft = fit[0]
                    return (
                        f"Masz jeszcze około **{slack} min** do momentu wyjścia na **{title}**.\n"
                        f"Najlepszy następny krok: **{_task_title(task_soft)}** (~{_duration_min(task_soft)} min, p{_priority(task_soft)})."
                    )
            return prepare_for_next_task(tasks_mod, origin, default_mode, buffer_min=buffer_min)
        if now_min <= start_min + _duration_min(task):
            return prepare_for_next_task(tasks_mod, origin, default_mode, buffer_min=buffer_min)

    if untimed:
        task = untimed[0]
        return (
            f"Najlepszy następny krok: **{_task_title(task)}** (~{_duration_min(task)} min, p{_priority(task)}).\n"
            "To dobre miejsce na małe elastyczne zadanie przed zamknięciem dnia."
        )
    if timed:
        last_start, last_task = timed[-1]
        return (
            f"Na dziś nie widzę już kolejnego kroku po punkcie **{_fmt_hhmm(last_start)} {_task_title(last_task)}**.\n"
            "Możesz zamknąć dzień, zrobić przegląd inboxa albo zaplanować jutro."
        )
    return "Na dziś nie widzę już kolejnego kroku. Możesz zamknąć dzień albo zaplanować jutro."
