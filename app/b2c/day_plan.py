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


def _task_location_text(t: Dict[str, Any]) -> Optional[str]:
    for k in ("location_text", "location", "place", "address"):
        v = t.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _task_start_origin(t: Dict[str, Any], fallback_origin: Optional[str]) -> Optional[str]:
    v = t.get("start_origin")
    if isinstance(v, str) and v.strip():
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


def _checklist_lines(t: Dict[str, Any], max_items: int = 5) -> List[str]:
    cl = t.get("checklist")
    if not isinstance(cl, dict):
        return []
    title = cl.get("title") or "Lista"
    items = cl.get("items") or []
    if not isinstance(items, list) or not items:
        return []
    lines = [f"      {title}:"]
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
    remaining = len([i for i in items if i]) - shown
    if remaining > 0:
        lines.append(f"      (+{remaining} więcej)")
    return lines


def build_day_plan(
    tasks: List[Dict[str, Any]],
    day_iso: str,
    origin_addr: Optional[str],
    transport_mode: Optional[str],
    buffer_min: int = 10,
) -> str:
    header = f"PLAN DNIA — {day_iso}"
    lines: List[str] = [header, ""]

    def _sort_key(t: Dict[str, Any]):
        hhmm = _parse_hhmm(str(t.get("time") or "")) or _parse_hhmm(str(t.get("due_at") or "").split("T", 1)[1][:5] if "T" in str(t.get("due_at") or "") else "")
        return (0, hhmm[0], hhmm[1]) if hhmm else (1, 99, 99)

    tasks_sorted = sorted(tasks or [], key=_sort_key)

    if not tasks_sorted:
        return header + "\n\nBrak zadań na dziś."

    for t in tasks_sorted:
        time_str = str(t.get("time") or "").strip()
        if not time_str:
            due_at = str(t.get("due_at") or "")
            if "T" in due_at:
                time_str = due_at.split("T", 1)[1][:5]

        title = _task_title(t)
        loc = _task_location_text(t)

        if time_str:
            lines.append(f"{time_str}  {title}" + (f" — {loc}" if loc else ""))
        else:
            lines.append(f"(bez godz.)  {title}" + (f" — {loc}" if loc else ""))

        task_origin = _task_start_origin(t, origin_addr)
        task_mode = _task_travel_mode(t, transport_mode)
        leave_at = (t.get("leave_at") or "").strip() if isinstance(t.get("leave_at"), str) else ""
        eta_saved = t.get("eta_min")

        if task_origin and task_mode:
            if leave_at and isinstance(eta_saved, int):
                lines.append(f"      Start: {task_origin}  • Wyjazd: {leave_at}  • Dojazd: {eta_saved} min  • Tryb: {task_mode}")
            elif time_str and loc:
                gm = (task_mode or "").strip().lower()
                gm = {
                    "samochod": "driving",
                    "samochód": "driving",
                    "samochodem": "driving",
                    "autobus": "transit",
                    "komunikacja": "transit",
                    "komunikacją": "transit",
                    "rower": "bicycling",
                    "rowerem": "bicycling",
                    "pieszo": "walking",
                }.get(gm, gm or "driving")
                eta = None
                try:
                    eta = get_eta_minutes(task_origin, loc, gm)
                except Exception:
                    eta = None

                if isinstance(eta, int) and eta > 0:
                    hhmm = _parse_hhmm(time_str)
                    if hhmm:
                        try:
                            dt_task = datetime.fromisoformat(day_iso + "T00:00:00").replace(hour=hhmm[0], minute=hhmm[1])
                            dt_depart = dt_task - timedelta(minutes=int(eta) + int(buffer_min))
                            lines.append(f"      Start: {task_origin}  • Wyjazd: {_fmt_dt(dt_depart)}  • Dojazd: {eta} min  • Tryb: {task_mode}")
                        except Exception:
                            lines.append(f"      Start: {task_origin}  • Dojazd: {eta} min  • Tryb: {task_mode}")
                else:
                    lines.append(f"      Start: {task_origin}  • Tryb: {task_mode}")

        lines.extend(_checklist_lines(t))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
