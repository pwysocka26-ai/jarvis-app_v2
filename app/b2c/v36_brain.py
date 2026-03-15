
from __future__ import annotations

from datetime import date, timedelta, datetime
from typing import Any, Dict, List, Optional, Tuple


def _to_min(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _fmt_hhmm(minutes: int) -> str:
    minutes = max(0, int(minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


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


def _travel_line(origin: Optional[str], location: str, default_mode: Optional[str]) -> Optional[str]:
    if not origin or not location:
        return None
    mode_map = {
        "samochodem": "driving",
        "komunikacją": "transit",
        "komunikacja": "transit",
        "rowerem": "bicycling",
        "pieszo": "walking",
    }
    mode = mode_map.get((default_mode or "samochodem").strip().lower(), "driving")
    try:
        from app.b2c.maps_google import get_eta_minutes
        eta = get_eta_minutes(origin, location, mode)
    except Exception:
        eta = None
    if eta is None:
        return None
    return f"ETA {eta} min • wyjście {_fmt_hhmm(_to_min('00:00'))}"  # placeholder replaced by caller


def _conflicts(rows: List[Dict[str, Any]]) -> List[str]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    risks = []
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        if a["end"] > b["start"]:
            risks.append(f"{_fmt_hhmm(a['start'])} {a['title']} ↔ {_fmt_hhmm(b['start'])} {b['title']}")
    return risks[:8]


def _free_windows(rows: List[Dict[str, Any]]) -> List[str]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"]))
    if not ordered:
        return []
    wins = []
    prev_end = ordered[0]["end"]
    for row in ordered[1:]:
        if row["start"] > prev_end:
            wins.append(f"{_fmt_hhmm(prev_end)}–{_fmt_hhmm(row['start'])}")
        prev_end = max(prev_end, row["end"])
    return wins[:5]


def calendar_brain(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["kind"], r["title"]))

    title = "CALENDAR BRAIN"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Brak punktów w kalendarzu na ten dzień.")
        return "\n".join(lines)

    lines.append("Oś dnia:")
    for row in rows:
        kind = "📅" if row["kind"] == "event" else "✅"
        line = f"{kind} {row['time']} — {row['title']}"
        if row.get("location"):
            line += f" ({row['location']})"
        lines.append(line)
        if row.get("location") and origin:
            mode_map = {
                "samochodem": "driving",
                "komunikacją": "transit",
                "komunikacja": "transit",
                "rowerem": "bicycling",
                "pieszo": "walking",
            }
            mode = mode_map.get((row.get("travel_mode") or default_mode or "samochodem").strip().lower(), "driving")
            try:
                from app.b2c.maps_google import get_eta_minutes
                eta = get_eta_minutes(origin, row["location"], mode)
            except Exception:
                eta = None
            if eta is not None:
                leave = row["start"] - eta - 10
                lines.append(f"   dojazd: ETA {eta} min • wyjście {_fmt_hhmm(leave)}")
    risks = _conflicts(rows)
    if risks:
        lines.extend(["", "Konflikty czasowe:"])
        lines.extend(f"• {r}" for r in risks)
    else:
        lines.extend(["", "Konflikty czasowe:", "• Brak wykrytych konfliktów."])

    wins = _free_windows(rows)
    if wins:
        lines.extend(["", "Wolne okna:"])
        lines.extend(f"• {w}" for w in wins)
    return "\n".join(lines)
