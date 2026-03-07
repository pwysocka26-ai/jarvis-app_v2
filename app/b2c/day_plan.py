from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.b2c.maps_google import get_eta_minutes


def _parse_hhmm(s: str) -> Optional[Tuple[int, int]]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        hh, mm = s.split(":", 1)
        return int(hh), int(mm)
    except Exception:
        return None


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _display_mode(mode: Optional[str]) -> Optional[str]:
    low = (mode or "").strip().lower()
    mapping = {
        "samochod": "samochodem",
        "samochód": "samochodem",
        "samochodem": "samochodem",
        "driving": "samochodem",
        "car": "samochodem",
        "autobus": "komunikacją",
        "komunikacja": "komunikacją",
        "komunikacją": "komunikacją",
        "transit": "komunikacją",
        "rower": "rowerem",
        "rowerem": "rowerem",
        "bicycling": "rowerem",
        "bike": "rowerem",
        "pieszo": "pieszo",
        "walking": "pieszo",
        "walk": "pieszo",
    }
    return mapping.get(low, (mode or "").strip() or None)


def _maps_mode(mode: Optional[str]) -> str:
    low = (mode or "").strip().lower()
    mapping = {
        "samochod": "driving",
        "samochód": "driving",
        "samochodem": "driving",
        "driving": "driving",
        "car": "driving",
        "autobus": "transit",
        "komunikacja": "transit",
        "komunikacją": "transit",
        "transit": "transit",
        "rower": "bicycling",
        "rowerem": "bicycling",
        "bicycling": "bicycling",
        "bike": "bicycling",
        "pieszo": "walking",
        "walking": "walking",
        "walk": "walking",
    }
    return mapping.get(low, "driving")


def _task_location_text(t: Dict[str, Any]) -> Optional[str]:
    for k in ("location", "location_text", "place", "address"):
        v = t.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _task_start_origin(t: Dict[str, Any], fallback_origin: Optional[str]) -> Optional[str]:
    v = t.get("start_origin")
    if isinstance(v, str) and v.strip():
        low = v.strip().lower()
        if low in {"dom", "home", "praca", "work", "tu", "tutaj"} and fallback_origin:
            return fallback_origin
        return v.strip()
    return fallback_origin


def _task_travel_mode(t: Dict[str, Any], fallback_mode: Optional[str]) -> Optional[str]:
    for k in ("travel_mode", "mode"):
        v = t.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return fallback_mode


def _task_title(t: Dict[str, Any]) -> str:
    for k in ("title", "text", "name"):
        v = t.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return f"Zadanie #{t.get('id', '?')}"


def _time_str_from_task(t: Dict[str, Any]) -> str:
    time_str = str(t.get("time") or "").strip()
    if time_str:
        return time_str[:5]
    due_at = str(t.get("due_at") or "")
    if "T" in due_at:
        return due_at.split("T", 1)[1][:5]
    return ""


def _sort_key(t: Dict[str, Any]):
    hhmm = _parse_hhmm(_time_str_from_task(t))
    return (0, hhmm[0], hhmm[1], int(t.get("id") or 0)) if hhmm else (1, 99, 99, int(t.get("id") or 0))


def _checklist_lines(t: Dict[str, Any], max_items: int = 10) -> List[str]:
    cl = t.get("checklist")
    if not isinstance(cl, dict):
        return []
    items = cl.get("items") or []
    if not isinstance(items, list) or not items:
        return []
    lines: List[str] = []
    shown = 0
    for it in items:
        if shown >= max_items:
            break
        if isinstance(it, dict):
            txt = (it.get("text") or "").strip()
            done = bool(it.get("done"))
        else:
            txt = str(it).strip()
            done = False
        if not txt:
            continue
        mark = "☑" if done else "☐"
        lines.append(f"      {mark} {txt}")
        shown += 1
    remaining = len(items) - shown
    if remaining > 0:
        lines.append(f"      (+{remaining} więcej)")
    return lines


def _compute_trip_fields(
    task: Dict[str, Any],
    day_iso: str,
    origin_addr: Optional[str],
    transport_mode: Optional[str],
    buffer_min: int,
):
    start_origin = _task_start_origin(task, origin_addr)
    raw_mode = _task_travel_mode(task, transport_mode)
    mode_display = _display_mode(raw_mode)

    saved_leave_at = task.get("leave_at")
    leave_at = saved_leave_at.strip() if isinstance(saved_leave_at, str) and saved_leave_at.strip() else None

    eta_val = task.get("eta_min")
    eta_min = int(eta_val) if isinstance(eta_val, int) and eta_val > 0 else None

    if leave_at or eta_min:
        return start_origin, eta_min, leave_at, mode_display

    time_str = _time_str_from_task(task)
    loc = _task_location_text(task)
    if not (time_str and loc and start_origin):
        return start_origin, None, None, mode_display

    eta_live = None
    try:
        eta_live = get_eta_minutes(start_origin, loc, _maps_mode(raw_mode))
    except Exception:
        eta_live = None

    if not (isinstance(eta_live, int) and eta_live > 0):
        return start_origin, None, None, mode_display

    leave_calc = None
    hhmm = _parse_hhmm(time_str)
    if hhmm:
        try:
            dt_task = datetime.fromisoformat(day_iso + "T00:00:00").replace(hour=hhmm[0], minute=hhmm[1])
            dt_depart = dt_task - timedelta(minutes=int(eta_live) + int(buffer_min))
            leave_calc = _fmt_dt(dt_depart)
        except Exception:
            leave_calc = None

    return start_origin, int(eta_live), leave_calc, mode_display


def build_day_plan(
    tasks: List[Dict[str, Any]],
    day_iso: str,
    origin_addr: Optional[str],
    transport_mode: Optional[str],
    buffer_min: int = 10,
) -> str:
    header = f"PLAN DNIA — {day_iso}"
    if not tasks:
        return header + "\n\nBrak zadań na dziś."

    tasks_sorted = sorted(tasks, key=_sort_key)
    lines: List[str] = [header, ""]

    for task in tasks_sorted:
        title = _task_title(task)
        time_str = _time_str_from_task(task)
        location = _task_location_text(task)

        start_origin, eta_min, leave_at, mode_display = _compute_trip_fields(
            task, day_iso, origin_addr, transport_mode, buffer_min
        )

        if leave_at:
            lines.append(f"{leave_at}  WYJŚCIE → {title}")
            lines.append("")

        headline = f"{time_str}  {title}" if time_str else f"(bez godz.)  {title}"
        if location:
            headline += f" — {location}"
        lines.append(headline)

        details: List[str] = []
        if start_origin:
            details.append(f"Start: {start_origin}")
        if eta_min:
            details.append(f"Dojazd: {eta_min} min")
        if mode_display:
            details.append(f"Tryb: {mode_display}")
        if details:
            lines.append("      " + "  •  ".join(details))

        lines.extend(_checklist_lines(task))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
