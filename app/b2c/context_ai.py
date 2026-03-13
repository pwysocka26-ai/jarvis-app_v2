from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import json
import os

from app.b2c.maps_google import get_eta_minutes
from app.b2c.cognitive_layer import energy_advice, memory_summary, log_memory_event

DAY_START_MIN = 6 * 60
DAY_END_MIN = 21 * 60
DEFAULT_BUFFER_MIN = 10


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

    windows = _free_windows(timed) if timed else [(9 * 60, 18 * 60)]
    if untimed:
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
        if windows:
            biggest = max(windows, key=lambda w: w[1] - w[0])
            lines.append(f"Największe wolne okno dziś: **{_fmt_hhmm(biggest[0])}–{_fmt_hhmm(biggest[1])}** ({biggest[1]-biggest[0]} min).")
            lines.append("Możesz w tym czasie odpocząć, ogarnąć inbox albo zaplanować jutro.")

    if timed:
        lines.extend(["", assess_all_today_schedule(tasks_mod, origin, default_mode, buffer_min=buffer_min)])
    return "\n".join(lines)


def suggest_now_with_limit(tasks_mod, minutes: int) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    limit = max(5, int(minutes))

    windows = _free_windows(timed) if timed else [(DAY_START_MIN, DAY_END_MIN)]
    current = [(max(a, now_min), b) for a, b in windows if b - max(a, now_min) >= 5]
    usable = [w for w in current if w[1] - w[0] >= limit]

    if not usable and windows:
        biggest = max(windows, key=lambda w: w[1] - w[0])
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

    if not usable:
        return f"Nie widzę już dziś wolnego okna na około {limit} min.\n" + "\n".join(_generic_suggestions())

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
        biggest = max(free, key=lambda w: w[1]-w[0])
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
    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    if not timed:
        return "Nie widzę już dziś kolejnego zadania z godziną."

    upcoming = [(s, t) for s, t in timed if s >= now_min]
    if upcoming:
        start_min, task = upcoming[0]
        status = _human_delta(start_min, now_min)
    else:
        tomorrow = _timed_tasks(_tomorrow_tasks(tasks_mod))
        if tomorrow:
            start_min, task = tomorrow[0]
            status = "jutro"
        else:
            start_min, task = timed[-1]
            status = "to był ostatni dzisiejszy punkt"

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
                lines.append(f"• {item.get('text','').strip()}")
            else:
                lines.append(f"• {str(item).strip()}")
    else:
        lines.append("")
        lines.append("Do tego czasu możesz:")
        lines.extend(_generic_suggestions()[:2])
    return "\n".join(lines)


def plan_whole_day(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    base = auto_plan_day(tasks_mod, origin, default_mode, buffer_min=buffer_min)
    extra = suggest_for_free_time(tasks_mod)
    return base + "\n\n" + extra


def _current_window(tasks_mod) -> Optional[Tuple[int, int]]:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    windows = _free_windows(timed) if timed else [(DAY_START_MIN, DAY_END_MIN)]
    usable = []
    for start_w, end_w in windows:
        start_eff = max(start_w, now_min)
        if end_w - start_eff >= 5:
            usable.append((start_eff, end_w))
    if usable:
        usable.sort(key=lambda w: (w[0] > now_min, w[0]))
        return usable[0]
    return None


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
    if free:
        biggest = max(free, key=lambda w: w[1] - w[0])
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
    win = _current_window(tasks_mod)
    if not win:
        return "Nie widzę już dziś sensownego wolnego okna. Został tylko ostatni punkt albo dzień jest domknięty."
    start_w, end_w = win
    gap = end_w - start_w
    lines = [f"Aktualne okno: **{_fmt_hhmm(start_w)}–{_fmt_hhmm(end_w)}** ({gap} min)."]
    fit = [t for t in untimed if _duration_min(t) <= gap]
    if fit:
        lines.extend(["", "W tym oknie zmieści się:"])
        for task in fit[:4]:
            lines.append(f"• {_task_title(task)} (~{_duration_min(task)} min, p{_priority(task)})")
    else:
        lines.extend(["", "Nie widzę dziś zadania bez godziny, które idealnie pasuje do tego okna."])
        lines.extend(_generic_suggestions())
    return "\n".join(lines)


def daily_next_step(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    if timed:
        next_start, next_task = None, None
        for start_min, task in timed:
            if start_min >= now_min:
                next_start, next_task = start_min, task
                break
        if next_task is not None:
            title = _task_title(next_task)
            loc = _task_location(next_task)
            mode = next_task.get('travel_mode') or default_mode or 'samochod'
            eta = _eta_minutes(origin, loc, mode) if origin and loc else 0
            leave = next_start - eta - buffer_min if eta else next_start
            if now_min >= leave:
                base = prepare_for_next_task(tasks_mod, origin, default_mode, buffer_min=buffer_min)
                return "Najbliższy krok to przygotować się do wyjścia.\n\n" + base
            slack = leave - now_min
            if slack >= 20 and untimed:
                fit = [t for t in untimed if _duration_min(t) <= slack]
                if fit:
                    task = fit[0]
                    return (
                        f"Masz jeszcze około **{slack} min** do momentu wyjścia na **{title}**.\n"
                        f"Najlepszy następny krok: **{_task_title(task)}** (~{_duration_min(task)} min, p{_priority(task)})."
                    )
            return prepare_for_next_task(tasks_mod, origin, default_mode, buffer_min=buffer_min)

    if untimed:
        task = untimed[0]
        return f"Najlepszy następny krok: **{_task_title(task)}** (~{_duration_min(task)} min, p{_priority(task)})."
    return "Na dziś nie widzę już kolejnego kroku. Możesz zamknąć dzień albo zaplanować jutro."


def dynamic_day_reply(tasks_mod, delay_min: int, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get("created_at") or "")))
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    delay_min = max(0, int(delay_min or 0))

    lines = [f"DYNAMIC DAY — {_today_iso()}", ""]
    if not timed and not untimed:
        return "Na dziś nie mam żadnych zadań do przeplanowania."

    if delay_min:
        lines.append(f"Uwzględniam opóźnienie: **{delay_min} min**.")
    else:
        lines.append("Przeliczam plan od teraz.")

    anchor = now_min + delay_min
    future_timed = [(s, t) for s, t in timed if s >= anchor]
    if future_timed:
        lines.append("")
        lines.append("Najbliższe stałe punkty po korekcie:")
        for s, t in future_timed[:5]:
            lines.append(f"• {_fmt_hhmm(s)} {_task_title(t)}")
    else:
        lines.append("")
        lines.append("Nie masz już dziś kolejnych twardych punktów po tej korekcie.")

    horizon_end = DAY_END_MIN
    if future_timed:
        first_future = future_timed[0][0]
        if first_future - anchor >= 15:
            lines.append("")
            lines.append(f"Masz okno **{_fmt_hhmm(anchor)}–{_fmt_hhmm(first_future)}** ({first_future-anchor} min).")
            fit = [t for t in untimed if _duration_min(t) <= max(15, first_future-anchor)]
            if fit:
                lines.append("W tym czasie zmieści się:")
                for t in fit[:3]:
                    lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
        else:
            lines.append("")
            lines.append("Do najbliższego punktu nie ma już dużego bufora — skup się na domknięciu bieżącej rzeczy i przygotowaniu wyjścia.")
    else:
        if untimed:
            lines.append("")
            lines.append(f"Do końca dnia zostało okno **{_fmt_hhmm(anchor)}–{_fmt_hhmm(horizon_end)}** ({max(0,horizon_end-anchor)} min).")
            lines.append("Najlepiej teraz zrobić:")
            for t in untimed[:3]:
                lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
        else:
            lines.append("")
            lines.extend(_generic_suggestions())

    log_memory_event('dynamic_day', {'delay_min': delay_min, 'future_fixed': len(future_timed), 'untimed': len(untimed)})
    return "\n".join(lines)


def energy_day_reply(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    untimed = sorted(_untimed_tasks(tasks), key=lambda t: (_priority(t), str(t.get('created_at') or '')) )
    timed = _timed_tasks(tasks)
    advice = energy_advice(tasks)
    log_memory_event('energy_check', {'tasks_today': len(tasks)})
    lines = [advice]
    if untimed:
        lines.append("")
        lines.append("Najlepsze elastyczne zadania na ten poziom energii:")
        for t in untimed[:3]:
            lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
    elif timed:
        lines.append("")
        lines.append("Masz dziś głównie stałe punkty — między nimi zostaw sobie tylko lekkie mikro-rzeczy.")
    return "\n".join(lines)


def memory_brain_reply(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    summary = memory_summary(tasks)
    log_memory_event('memory_check', {'tasks_today': len(tasks)})
    return summary

_BRAIN_FILE = os.path.join("data", "memory", "brain_patterns.json")


def _brain_tokens_from_tasks(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    buckets: Dict[str, int] = {}
    for t in tasks:
        title = _task_title(t).lower()
        for token in ["mail", "inbox", "telefon", "zakupy", "trening", "notatk", "pomysł", "pomysl", "sprząt", "sprzat"]:
            if token in title:
                buckets[token] = buckets.get(token, 0) + 1
    return buckets


def _load_persistent_brain() -> Dict[str, Any]:
    try:
        if os.path.exists(_BRAIN_FILE):
            with open(_BRAIN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {
        "days_seen": 0,
        "last_day": "",
        "task_type_counts": {},
        "duration_profile": {"short": 0, "medium": 0, "long": 0},
        "time_of_day": {"morning": 0, "afternoon": 0, "evening": 0},
    }


def _save_persistent_brain(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_BRAIN_FILE), exist_ok=True)
    with open(_BRAIN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _duration_profile_from_tasks(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {"short": 0, "medium": 0, "long": 0}
    for t in tasks:
        dur = _duration_min(t)
        if dur <= 20:
            out["short"] += 1
        elif dur <= 40:
            out["medium"] += 1
        else:
            out["long"] += 1
    return out


def _time_profile_from_timed(timed: List[Tuple[int, Dict[str, Any]]]) -> Dict[str, int]:
    out = {"morning": 0, "afternoon": 0, "evening": 0}
    for start, _ in timed:
        if start < 12 * 60:
            out["morning"] += 1
        elif start < 18 * 60:
            out["afternoon"] += 1
        else:
            out["evening"] += 1
    return out


def _merge_counts(base: Dict[str, int], add: Dict[str, int]) -> Dict[str, int]:
    merged = dict(base)
    for k, v in add.items():
        merged[k] = int(merged.get(k, 0)) + int(v)
    return merged


def _update_persistent_brain(tasks_mod) -> Dict[str, Any]:
    data = _load_persistent_brain()
    today = _today_iso()
    if data.get("last_day") == today:
        return data

    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)

    data["days_seen"] = int(data.get("days_seen", 0)) + 1
    data["last_day"] = today
    data["task_type_counts"] = _merge_counts(data.get("task_type_counts", {}), _brain_tokens_from_tasks(tasks))
    data["duration_profile"] = _merge_counts(data.get("duration_profile", {}), _duration_profile_from_tasks(tasks))
    data["time_of_day"] = _merge_counts(data.get("time_of_day", {}), _time_profile_from_timed(timed))
    _save_persistent_brain(data)
    return data

def smart_task_brain_reply(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    lines = [f"SMART TASK BRAIN — {_today_iso()}", ""]
    try:
        next_step = daily_next_step(tasks_mod, origin, default_mode, buffer_min=buffer_min)
        if next_step:
            lines.append(next_step)
    except Exception:
        lines.append("Nie mogę jeszcze wskazać najlepszego następnego kroku.")
    try:
        window_reply = suggest_for_current_window(tasks_mod, origin, default_mode, buffer_min=buffer_min)
        if window_reply:
            lines.extend(["", window_reply])
    except Exception:
        pass
    try:
        energy_reply = energy_day_reply(tasks_mod)
        if energy_reply:
            lines.extend(["", energy_reply])
    except Exception:
        pass
    return "\n".join(lines)

def learning_brain_reply(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = _untimed_tasks(tasks)

    title_buckets = _brain_tokens_from_tasks(tasks)
    duration_buckets = _duration_profile_from_tasks(tasks)

    lines = [f"LEARNING BRAIN — {_today_iso()}", ""]
    lines.append(f"Dziś widzę {len(tasks)} zadań: {len(timed)} z godziną i {len(untimed)} elastycznych.")
    if title_buckets:
        lines.extend(["", "Najczęstsze typy zadań dziś:"])
        for name, count in sorted(title_buckets.items(), key=lambda kv: (-kv[1], kv[0]))[:5]:
            lines.append(f"• {name}: {count}")
    lines.extend(["", "Szacowany profil dnia:"])
    lines.append(f"• krótkie bloki: {duration_buckets['short']}")
    lines.append(f"• średnie bloki: {duration_buckets['medium']}")
    lines.append(f"• dłuższe bloki: {duration_buckets['long']}")
    return "\n".join(lines)

def memory_patterns_reply(tasks_mod) -> str:
    tasks = _today_tasks(tasks_mod)
    timed = _timed_tasks(tasks)
    untimed = _untimed_tasks(tasks)

    morning = sum(1 for start, _ in timed if start < 12 * 60)
    afternoon = sum(1 for start, _ in timed if 12 * 60 <= start < 18 * 60)
    evening = sum(1 for start, _ in timed if start >= 18 * 60)

    lines = [f"MEMORY PATTERNS — {_today_iso()}", ""]
    lines.append(f"Stałe punkty: rano {morning}, popołudnie {afternoon}, wieczór {evening}.")
    lines.append(f"Elastyczne zadania dziś: {len(untimed)}.")
    if morning >= afternoon and morning >= evening:
        lines.append("Wzorzec dnia: dziś najwięcej dzieje się rano.")
    elif afternoon >= evening:
        lines.append("Wzorzec dnia: dziś główny ciężar planu jest po południu.")
    else:
        lines.append("Wzorzec dnia: dziś więcej rzeczy przesuwa się na wieczór.")
    if untimed:
        top = sorted(untimed, key=lambda t: (_priority(t), str(t.get("created_at") or "")))[:3]
        lines.extend(["", "Najbardziej typowe elastyczne zadania dziś:"])
        for t in top:
            lines.append(f"• {_task_title(t)} (~{_duration_min(t)} min, p{_priority(t)})")
    return "\n".join(lines)

def predictive_planner_reply(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = DEFAULT_BUFFER_MIN) -> str:
    lines = [f"PREDICTIVE PLANNER — {_today_iso()}", ""]
    try:
        lines.append(daily_next_step(tasks_mod, origin, default_mode, buffer_min=buffer_min))
    except Exception:
        pass
    try:
        lines.extend(["", suggest_for_current_window(tasks_mod, origin, default_mode, buffer_min=buffer_min)])
    except Exception:
        pass
    try:
        lines.extend(["", memory_patterns_reply(tasks_mod)])
    except Exception:
        pass
    return "\n".join([line for line in lines if line is not None])

def inbox_intelligence_reply() -> str:
    try:
        from app.b2c import inbox as inbox_mod
        data = inbox_mod.list_inbox()
        items = data if isinstance(data, list) else data.get("items", [])
    except Exception:
        items = []

    if not items:
        return "INBOX INTELLIGENCE\n\nInbox jest pusty albo nie mam jeszcze czego przeanalizować."

    lines = ["INBOX INTELLIGENCE", "", "Potencjalne taski z inboxa:"]
    count = 0
    for item in items[:10]:
        text = str(item.get("text") or item.get("title") or "").strip()
        low = text.lower()
        if any(k in low for k in ["zadzwo", "napisz", "umów", "umow", "kup", "przygotuj", "wyślij", "wyslij", "oddaj", "sprawdź", "sprawdz"]):
            lines.append(f"• {text}")
            count += 1
    if count == 0:
        lines.append("• Nie widzę jeszcze wyraźnych zadań — wygląda bardziej na notatki i pomysły.")
    return "\n".join(lines)

def persist_today_patterns_reply(tasks_mod) -> str:
    data = _update_persistent_brain(tasks_mod)
    return f"Trwała pamięć zaktualizowana. Zapisane dni: {data.get('days_seen', 0)}."

def persistent_brain_reply(tasks_mod) -> str:
    data = _update_persistent_brain(tasks_mod)

    lines = ["PERSISTENT BRAIN", ""]
    lines.append(f"Zapamiętane dni: {data.get('days_seen', 0)}")

    type_counts = data.get("task_type_counts", {})
    if type_counts:
        lines.extend(["", "Najczęstsze typy zadań między dniami:"])
        for name, count in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]:
            lines.append(f"• {name}: {count}")

    dur = data.get("duration_profile", {})
    lines.extend(["", "Profil bloków między dniami:"])
    lines.append(f"• krótkie: {int(dur.get('short', 0))}")
    lines.append(f"• średnie: {int(dur.get('medium', 0))}")
    lines.append(f"• długie: {int(dur.get('long', 0))}")

    tod = data.get("time_of_day", {})
    lines.extend(["", "Rytm dnia między dniami:"])
    lines.append(f"• rano: {int(tod.get('morning', 0))}")
    lines.append(f"• popołudnie: {int(tod.get('afternoon', 0))}")
    lines.append(f"• wieczór: {int(tod.get('evening', 0))}")

    dominant = max([("rano", int(tod.get("morning", 0))), ("po południu", int(tod.get("afternoon", 0))), ("wieczorem", int(tod.get("evening", 0)))], key=lambda x: x[1])[0]
    lines.extend(["", f"Wniosek: najwięcej rzeczy zwykle dzieje się {dominant}."])
    return "\n".join(lines)
