
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

DAY_START = 8 * 60
DAY_END = 20 * 60
LUNCH_EARLIEST = 12 * 60
LUNCH_LATEST = 14 * 60
SHORT_BREAK = 10
FOCUS_MIN = 45


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
        })
    return rows


def _free_windows(rows: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    if not ordered:
        return [(DAY_START, DAY_END)]
    out: List[Tuple[int, int]] = []
    cur = DAY_START
    for row in ordered:
        if row["start"] > cur:
            out.append((cur, row["start"]))
        cur = max(cur, row["end"])
    if cur < DAY_END:
        out.append((cur, DAY_END))
    return out


def _lunch_block(free_windows: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    for start, end in free_windows:
        s = max(start, LUNCH_EARLIEST)
        e = min(end, LUNCH_LATEST)
        if e - s >= 30:
            return (s, s + 30)
    return None


def _focus_blocks(free_windows: List[Tuple[int, int]], lunch: Optional[Tuple[int, int]]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for start, end in free_windows:
        segments = [(start, end)]
        if lunch and not (lunch[1] <= start or lunch[0] >= end):
            segments = []
            if lunch[0] > start:
                segments.append((start, lunch[0]))
            if lunch[1] < end:
                segments.append((lunch[1], end))
        for s, e in segments:
            if e - s >= FOCUS_MIN:
                out.append((s, e))
    return out[:4]


def _short_breaks(rows: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    out = []
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        gap = b["start"] - a["end"]
        if SHORT_BREAK <= gap <= 30:
            out.append((a["end"], min(a["end"] + SHORT_BREAK, b["start"])))
    return out[:6]


def smart_time_blocks(tasks_mod, day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "SMART TIME BLOCKS"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Brak punktów na ten dzień.")
        return "\n".join(lines)

    lines.append("Stałe punkty dnia:")
    for row in rows:
        kind = "📅" if row["kind"] == "event" else "✅"
        line = f"{kind} {_fmt_hhmm(row['start'])}–{_fmt_hhmm(row['end'])} {row['title']}"
        if row.get("location"):
            line += f" ({row['location']})"
        lines.append(line)

    free_windows = _free_windows(rows)
    lunch = _lunch_block(free_windows)
    breaks = _short_breaks(rows)
    focus = _focus_blocks(free_windows, lunch)

    if breaks:
        lines.extend(["", "Sugerowane krótkie przerwy:"])
        for s, e in breaks:
            lines.append(f"• {_fmt_hhmm(s)}–{_fmt_hhmm(e)}")
    if lunch:
        lines.extend(["", "Sugerowany lunch:"])
        lines.append(f"• {_fmt_hhmm(lunch[0])}–{_fmt_hhmm(lunch[1])}")
    if focus:
        lines.extend(["", "Sugerowane bloki focus:"])
        for s, e in focus:
            label = "focus"
            if e - s >= 90:
                lines.append(f"• {_fmt_hhmm(s)}–{_fmt_hhmm(min(s+90, e))} {label}")
            else:
                lines.append(f"• {_fmt_hhmm(s)}–{_fmt_hhmm(e)} {label}")

    if free_windows:
        lines.extend(["", "Wolne okna dnia:"])
        for s, e in free_windows[:6]:
            lines.append(f"• {_fmt_hhmm(s)}–{_fmt_hhmm(e)}")

    return "\n".join(lines)
