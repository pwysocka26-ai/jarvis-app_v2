
from __future__ import annotations

from datetime import date, timedelta
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


def _free_windows(rows: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"]))
    if not ordered:
        return []
    wins: List[Tuple[int, int]] = []
    prev_end = ordered[0]["end"]
    for row in ordered[1:]:
        if row["start"] > prev_end:
            wins.append((prev_end, row["start"]))
        prev_end = max(prev_end, row["end"])
    return wins


def _conflicts(rows: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    risks = []
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        if a["end"] > b["start"]:
            risks.append((a, b))
    return risks


def _choose_target_window(conf_row: Dict[str, Any], rows: List[Dict[str, Any]]) -> Optional[Tuple[int, int]]:
    duration = max(15, int(conf_row["end"] - conf_row["start"]))
    wins = _free_windows(rows)
    for start, end in wins:
        if end - start >= duration:
            return (start, start + duration)
    if rows:
        last_end = max(r["end"] for r in rows)
        return (last_end + 15, last_end + 15 + duration)
    return None


def _load_events_for_date(date_iso: str) -> List[Dict[str, Any]]:
    try:
        from app.b2c.v34_brain import _load_events
        return [e for e in _load_events() if str(e.get("date") or "") == date_iso]
    except Exception:
        return []


def _save_events(items: List[Dict[str, Any]]) -> None:
    from app.b2c.v34_brain import _save_events
    _save_events(items)


def _suggestions(rows: List[Dict[str, Any]]) -> List[str]:
    suggestions: List[str] = []
    for a, b in _conflicts(rows):
        target = b
        slot = _choose_target_window(target, rows)
        if slot:
            suggestions.append(
                f"• Przesuń `{target['title']}` z {_fmt_hhmm(target['start'])} na {_fmt_hhmm(slot[0])}."
            )
        else:
            suggestions.append(
                f"• Rozważ usunięcie albo skrócenie `{target['title']}`."
            )
    return suggestions[:8]


def scheduler_ai(tasks_mod, day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "SCHEDULER AI"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Nie mam nic do zaplanowania na ten dzień.")
        return "\n".join(lines)

    conflicts = _conflicts(rows)
    if not conflicts:
        lines.append("Nie widzę konfliktów. Plan wygląda stabilnie.")
        return "\n".join(lines)

    lines.append("Wykryte konflikty:")
    for a, b in conflicts[:8]:
        lines.append(f"• {_fmt_hhmm(a['start'])} {a['title']} ↔ {_fmt_hhmm(b['start'])} {b['title']}")
    lines.extend(["", "Proponowane naprawy:"])
    lines.extend(_suggestions(rows))
    lines.extend([
        "",
        "Możesz teraz wpisać:",
        "• `napraw plan dnia`",
        "• `napraw plan jutra`",
    ])
    return "\n".join(lines)


def _move_event(date_iso: str, title: str, old_time: str, new_time: str) -> bool:
    try:
        from app.b2c.v34_brain import _load_events, _save_events, _normalize_title
        items = _load_events()
        changed = False
        for item in items:
            if (
                str(item.get("date") or "") == date_iso
                and str(item.get("time") or "") == old_time
                and _normalize_title(str(item.get("title") or "")).lower() == _normalize_title(title).lower()
            ):
                item["time"] = new_time
                changed = True
                break
        if changed:
            _save_events(items)
        return changed
    except Exception:
        return False


def auto_repair_plan(tasks_mod, day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    conflicts = _conflicts(rows)
    title = "AUTO REPAIR PLAN"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not conflicts:
        lines.append("Nie było czego naprawiać. Plan już jest czysty.")
        return "\n".join(lines)

    repaired = []
    working_rows = list(rows)
    for a, b in conflicts:
        target_row = b
        slot = _choose_target_window(target_row, working_rows)
        if not slot:
            continue
        new_start, new_end = slot
        old_time = _fmt_hhmm(target_row["start"])
        new_time = _fmt_hhmm(new_start)
        if target_row["kind"] == "event":
            ok = _move_event(target, target_row["title"], old_time, new_time)
            if ok:
                repaired.append(f"• Przesunęłam wydarzenie `{target_row['title']}` z {old_time} na {new_time}.")
                target_row = dict(target_row)
                target_row["start"] = new_start
                target_row["end"] = new_end
                target_row["time"] = new_time
        # tasks are not auto-moved yet; only suggest
        working_rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    if not repaired:
        lines.append("Nie udało się automatycznie naprawić konfliktów.")
        lines.append("Spróbuj: `scheduler ai` żeby zobaczyć sugestie.")
        return "\n".join(lines)

    lines.append("Wprowadzone zmiany:")
    lines.extend(repaired)
    return "\n".join(lines)
