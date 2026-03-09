from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.b2c.day_plan import _compute_trip_fields, _task_location_text, _task_title, _time_str_from_task


DEFAULT_SLOT_MIN = 30


def _parse_hhmm(s: str) -> Optional[int]:
    s = (s or "").strip()
    if not s or ":" not in s:
        return None
    try:
        hh, mm = s.split(":", 1)
        h = int(hh)
        m = int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h * 60 + m
    except Exception:
        return None
    return None


def _fmt_hhmm(total_min: int) -> str:
    total_min = max(0, min(23 * 60 + 59, int(total_min)))
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def _duration_min(task: Dict[str, Any]) -> int:
    v = task.get("duration_min")
    if isinstance(v, int) and v > 0:
        return v
    cl = task.get("checklist")
    if isinstance(cl, dict) and isinstance(cl.get("items"), list) and cl.get("items"):
        return max(DEFAULT_SLOT_MIN, min(90, len(cl["items"]) * 10))
    return DEFAULT_SLOT_MIN


def _timed_tasks(tasks: List[Dict[str, Any]]) -> List[Tuple[int, Dict[str, Any]]]:
    out: List[Tuple[int, Dict[str, Any]]] = []
    for t in tasks or []:
        tm = _parse_hhmm(_time_str_from_task(t))
        if tm is not None:
            out.append((tm, t))
    out.sort(key=lambda x: (x[0], int(x[1].get("priority") or 9), int(x[1].get("id") or 0)))
    return out


def _task_line(task: Dict[str, Any], day_iso: str, origin_addr: Optional[str], transport_mode: Optional[str], buffer_min: int, start_min: int) -> str:
    title = _task_title(task)
    loc = _task_location_text(task)
    start_origin, eta_min, _leave_at, _mode = _compute_trip_fields(task, day_iso, origin_addr, transport_mode, buffer_min)
    label = f"{_fmt_hhmm(start_min)}  {title}"
    if loc:
        label += f" — {loc}"
    meta = []
    if eta_min:
        meta.append(f"ETA {eta_min} min")
    if start_origin and loc:
        meta.append(f"start: {start_origin}")
    if meta:
        label += "  •  " + "  •  ".join(meta)
    return label


def _collect_leave_events(tasks: List[Tuple[int, Dict[str, Any]]], day_iso: str, origin_addr: Optional[str], transport_mode: Optional[str], buffer_min: int) -> List[Tuple[int, str]]:
    events: List[Tuple[int, str]] = []
    for start_min, t in tasks or []:
        title = _task_title(t)
        start_origin, eta_min, leave_at, _mode = _compute_trip_fields(t, day_iso, origin_addr, transport_mode, buffer_min)
        if leave_at:
            lv = _parse_hhmm(leave_at)
            if lv is not None:
                label = f"{_fmt_hhmm(lv)}  WYJŚCIE → {title}"
                if eta_min:
                    label += f"  •  dojazd {eta_min} min"
                if start_origin:
                    label += f"  •  start: {start_origin}"
                events.append((lv, label))
    events.sort(key=lambda x: x[0])
    return events


def _free_windows(entries: List[Tuple[int, Dict[str, Any]]]) -> List[Tuple[int, int]]:
    if len(entries) < 2:
        return []
    windows: List[Tuple[int, int]] = []
    for idx in range(len(entries) - 1):
        cur_min, cur_task = entries[idx]
        next_min, _next_task = entries[idx + 1]
        end_cur = cur_min + _duration_min(cur_task)
        gap = next_min - end_cur
        if gap >= 30:
            windows.append((end_cur, next_min))
    return windows


def _conflicts(entries: List[Tuple[int, Dict[str, Any]]]) -> List[str]:
    out: List[str] = []
    for idx in range(len(entries) - 1):
        cur_min, cur_task = entries[idx]
        next_min, next_task = entries[idx + 1]
        cur_end = cur_min + _duration_min(cur_task)
        cur_title = _task_title(cur_task)
        next_title = _task_title(next_task)
        if next_min == cur_min:
            out.append(f"{_fmt_hhmm(cur_min)}: `{cur_title}` i `{next_title}` startują o tej samej porze.")
        elif next_min < cur_end:
            out.append(f"{_fmt_hhmm(cur_min)}–{_fmt_hhmm(cur_end)}: `{cur_title}` nachodzi na `{next_title}`.")
    return out


def _render_plan(title: str, timed: List[Tuple[int, Dict[str, Any]]], day_iso: str, origin_addr: Optional[str], transport_mode: Optional[str], buffer_min: int) -> str:
    lines: List[str] = [title, "", "Plan:"]
    leave_events = _collect_leave_events(timed, day_iso, origin_addr, transport_mode, buffer_min)
    merged: List[Tuple[int, str, int]] = [(m, txt, 0) for m, txt in leave_events]
    for start_min, task in timed:
        merged.append((start_min, _task_line(task, day_iso, origin_addr, transport_mode, buffer_min, start_min), 1))
    merged.sort(key=lambda x: (x[0], x[2], x[1]))
    for _m, txt, _kind in merged:
        bullet = "→" if "WYJŚCIE" in txt else "•"
        lines.append(f"{bullet} {txt}")

    free = _free_windows(timed)
    if free:
        lines.extend(["", "Wolne okna:"])
        for start_free, end_free in free[:5]:
            lines.append(f"• {_fmt_hhmm(start_free)}–{_fmt_hhmm(end_free)} ({end_free - start_free} min)")

    conflicts = _conflicts(timed)
    if conflicts:
        lines.extend(["", "Ryzyka / konflikty:"])
        for c in conflicts[:5]:
            lines.append(f"• {c}")
    return "\n".join(lines)


def build_smart_day_plan(tasks: List[Dict[str, Any]], day_iso: str, origin_addr: Optional[str], transport_mode: Optional[str], buffer_min: int = 10, now: Optional[datetime] = None) -> str:
    timed = _timed_tasks(tasks)
    if not timed:
        return f"SMART PLAN — {day_iso}\n\nNie mam dziś zadań z konkretną godziną."
    return _render_plan(f"SMART PLAN — {day_iso}", timed, day_iso, origin_addr, transport_mode, buffer_min)


def build_replanned_day_plan(tasks: List[Dict[str, Any]], day_iso: str, origin_addr: Optional[str], transport_mode: Optional[str], buffer_min: int = 10) -> str:
    timed = _timed_tasks(tasks)
    if not timed:
        return f"PRZEPLANOWANY DZIEŃ — {day_iso}\n\nNie mam dziś zadań z konkretną godziną."

    moved: List[str] = []
    replanned: List[Tuple[int, Dict[str, Any]]] = []
    current_end = None
    for start_min, task in timed:
        new_start = start_min
        if current_end is not None and new_start < current_end:
            new_start = current_end
            moved.append(f"{_task_title(task)} → {_fmt_hhmm(new_start)}")
        current_end = new_start + _duration_min(task)
        new_task = deepcopy(task)
        replanned.append((new_start, new_task))

    text = _render_plan(f"PRZEPLANOWANY DZIEŃ — {day_iso}", replanned, day_iso, origin_addr, transport_mode, buffer_min)
    if moved:
        text += "\n\nProponowane przesunięcia:\n" + "\n".join(f"• {x}" for x in moved[:8])
    else:
        text += "\n\nNie widzę konfliktów wymagających przesunięcia godzin."
    return text


def summarize_free_time(tasks: List[Dict[str, Any]], day_iso: str) -> str:
    timed = _timed_tasks(tasks)
    if len(timed) < 2:
        return "Nie mam dziś wystarczająco wielu zadań z godziną, żeby policzyć wolne okna."
    free = _free_windows(timed)
    if not free:
        return "Dziś nie widzę wolnego okna >= 30 min między zadaniami."
    total = sum(end - start for start, end in free)
    biggest = max(free, key=lambda x: x[1] - x[0])
    lines = [f"Wolny czas — {day_iso}", ""]
    lines.append(f"Łącznie masz około **{total} min** wolnego czasu między zadaniami.")
    lines.append(f"Największe okno: **{_fmt_hhmm(biggest[0])}–{_fmt_hhmm(biggest[1])}** ({biggest[1] - biggest[0]} min).")
    if len(free) > 1:
        lines.append("")
        lines.append("Pozostałe okna:")
        for start, end in free[:5]:
            lines.append(f"• {_fmt_hhmm(start)}–{_fmt_hhmm(end)} ({end - start} min)")
    return "\n".join(lines)
