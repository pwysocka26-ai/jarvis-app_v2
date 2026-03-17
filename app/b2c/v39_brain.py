
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


def _to_min(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _fmt_hhmm(minutes: int) -> str:
    minutes = max(0, int(minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _mode_to_google(mode: Optional[str]) -> str:
    low = (mode or "").strip().lower()
    if low in {"komunikacją", "komunikacja"}:
        return "transit"
    if low == "rowerem":
        return "bicycling"
    if low == "pieszo":
        return "walking"
    return "driving"


def _event_rows(target_date: str) -> List[Dict[str, Any]]:
    try:
        from app.b2c.v34_brain import _load_events
        items = _load_events()
    except Exception:
        return []
    rows = []
    for e in items:
        if str(e.get("date") or "") != target_date:
            continue
        t = str(e.get("time") or "")
        if not t:
            continue
        try:
            start = _to_min(t)
        except Exception:
            continue
        rows.append({
            "kind": "event",
            "title": str(e.get("title") or "wydarzenie"),
            "start": start,
            "end": start + 60,
            "location": str(e.get("location") or "").strip(),
            "time": t,
            "travel_mode": "",
        })
    return rows


def _task_rows(tasks_mod, target_date: str) -> List[Dict[str, Any]]:
    try:
        tasks = tasks_mod.list_tasks_for_date(target_date) or []
    except Exception:
        return []
    rows = []
    for t in tasks:
        due = str(t.get("due_at") or "")
        if "T" not in due:
            continue
        time_s = due.split("T", 1)[1][:5]
        try:
            start = _to_min(time_s)
        except Exception:
            continue
        try:
            duration = max(5, int(t.get("duration_min") or 30))
        except Exception:
            duration = 30
        rows.append({
            "kind": "task",
            "title": str(t.get("title") or t.get("text") or "zadanie").strip(),
            "start": start,
            "end": start + duration,
            "location": str(t.get("location") or "").strip(),
            "time": time_s,
            "travel_mode": str(t.get("travel_mode") or "").strip(),
        })
    return rows


def _eta_minutes(origin: Optional[str], destination: str, mode: Optional[str]) -> Optional[int]:
    if not origin or not destination:
        return None
    try:
        from app.b2c.maps_google import get_eta_minutes
        return get_eta_minutes(origin, destination, _mode_to_google(mode))
    except Exception:
        return None


def _logistic_conflicts(rows: List[Dict[str, Any]], origin: Optional[str], default_mode: Optional[str], buffer_min: int = 10) -> List[str]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    risks: List[str] = []

    prev_end = None
    prev_loc = origin
    for row in ordered:
        loc = str(row.get("location") or "").strip()
        mode = row.get("travel_mode") or default_mode
        if prev_end is not None and loc:
            eta = _eta_minutes(prev_loc, loc, mode)
            if eta is not None:
                leave_needed = row["start"] - eta - buffer_min
                if leave_needed < prev_end:
                    risks.append(
                        f"{_fmt_hhmm(prev_end)} → {_fmt_hhmm(row['start'])}: za mało czasu na dojazd do `{row['title']}` (ETA {eta} min)."
                    )
        prev_end = row["end"]
        prev_loc = loc or prev_loc
    return risks[:8]


def _time_conflicts(rows: List[Dict[str, Any]]) -> List[str]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    risks = []
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        if a["end"] > b["start"]:
            risks.append(f"{_fmt_hhmm(a['start'])} {a['title']} ↔ {_fmt_hhmm(b['start'])} {b['title']}")
    return risks[:8]


def travel_scheduler(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0, buffer_min: int = 10) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "TRAVEL SCHEDULER"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Brak punktów na ten dzień.")
        return "\n".join(lines)

    lines.append("Timeline z logistyką:")
    prev_loc = origin
    for idx, row in enumerate(rows, start=1):
        line = f"{idx}. {_fmt_hhmm(row['start'])}–{_fmt_hhmm(row['end'])} {row['title']}"
        if row.get("location"):
            line += f" ({row['location']})"
        lines.append(line)
        loc = str(row.get("location") or "").strip()
        mode = row.get("travel_mode") or default_mode
        if loc and prev_loc:
            eta = _eta_minutes(prev_loc, loc, mode)
            if eta is not None:
                leave = row["start"] - eta - buffer_min
                lines.append(f"   dojazd: ETA {eta} min • wyjście {_fmt_hhmm(leave)}")
        prev_loc = loc or prev_loc

    time_risks = _time_conflicts(rows)
    logistic_risks = _logistic_conflicts(rows, origin, default_mode, buffer_min=buffer_min)

    lines.extend(["", "Ocena dnia:"])
    if not time_risks and not logistic_risks:
        lines.append("✅ Nie widzę konfliktów czasowych ani logistycznych.")
    else:
        if time_risks:
            lines.append("⚠️ Konflikty czasowe:")
            lines.extend(f"• {r}" for r in time_risks)
        if logistic_risks:
            lines.append("⚠️ Konflikty logistyczne:")
            lines.extend(f"• {r}" for r in logistic_risks)

    if rows:
        first = rows[0]
        lines.extend(["", "Sugestia startu:"])
        lines.append(f"Zacznij od: {first['title']} o {_fmt_hhmm(first['start'])}.")
    return "\n".join(lines)


def auto_repair_travel_plan(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0, buffer_min: int = 10) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "AUTO REPAIR TRAVEL PLAN"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Nie mam nic do naprawy.")
        return "\n".join(lines)

    logistic_risks = _logistic_conflicts(rows, origin, default_mode, buffer_min=buffer_min)
    if not logistic_risks:
        lines.append("Nie widzę konfliktów logistycznych. Plan wygląda stabilnie.")
        return "\n".join(lines)

    lines.append("Wykryte ryzyka logistyczne:")
    lines.extend(f"• {r}" for r in logistic_risks)

    # This version is conservative: it suggests instead of mutating.
    lines.extend([
        "",
        "Proponowane działania:",
        "• Przesuń późniejsze wydarzenie na wolne okno po dojeździe.",
        "• Ustaw wcześniejsze wyjście z domu.",
        "• Zmień tryb dojazdu, jeśli to możliwe.",
    ])
    return "\n".join(lines)
