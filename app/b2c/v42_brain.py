
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

DAY_START = 6 * 60
DAY_END = 22 * 60
DEFAULT_DURATION = 60
BUFFER_MIN = 10


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


def _normalize_title(title: str) -> str:
    try:
        from app.b2c.v34_brain import _normalize_title
        return _normalize_title(title)
    except Exception:
        return str(title or "").strip()


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
            "end": start + DEFAULT_DURATION,
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


def _travel_need(prev_loc: Optional[str], row: Dict[str, Any], default_mode: Optional[str], buffer_min: int = BUFFER_MIN) -> Optional[Tuple[int, int]]:
    loc = str(row.get("location") or "").strip()
    if not prev_loc or not loc:
        return None
    eta = _eta_minutes(prev_loc, loc, row.get("travel_mode") or default_mode)
    if eta is None:
        return None
    leave = row["start"] - eta - buffer_min
    return eta, leave


def _time_conflicts(rows: List[Dict[str, Any]]) -> List[str]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    out = []
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        if a["end"] > b["start"]:
            out.append(f"{_fmt_hhmm(a['start'])} {a['title']} ↔ {_fmt_hhmm(b['start'])} {b['title']}")
    return out


def _travel_conflicts(rows: List[Dict[str, Any]], origin: Optional[str], default_mode: Optional[str], buffer_min: int = BUFFER_MIN) -> List[str]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    out = []
    prev_end = None
    prev_loc = origin
    for row in ordered:
        need = _travel_need(prev_loc, row, default_mode, buffer_min)
        if prev_end is not None and need is not None:
            eta, leave = need
            if leave < prev_end:
                out.append(f"`{row['title']}` wymaga wyjścia o {_fmt_hhmm(leave)} (ETA {eta} min).")
        prev_end = row["end"]
        prev_loc = str(row.get("location") or "").strip() or prev_loc
    return out


def _save_event_move(date_iso: str, title: str, old_time: str, new_time: str) -> bool:
    try:
        from app.b2c.v34_brain import _load_events, _save_events
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


def _simulate_from_order(rows: List[Dict[str, Any]], origin: Optional[str], default_mode: Optional[str], start_min: int = DAY_START) -> List[Dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    rebuilt = []
    current = start_min
    prev_loc = origin
    for row in ordered:
        duration = int(row["end"] - row["start"])
        loc = str(row.get("location") or "").strip()
        mode = row.get("travel_mode") or default_mode
        eta = _eta_minutes(prev_loc, loc, mode) if (prev_loc and loc) else None
        if eta is not None:
            current += eta + BUFFER_MIN
        new_row = dict(row)
        new_row["start"] = max(current, DAY_START)
        new_row["end"] = new_row["start"] + duration
        new_row["time"] = _fmt_hhmm(new_row["start"])
        rebuilt.append(new_row)
        current = new_row["end"]
        prev_loc = loc or prev_loc
    rebuilt.sort(key=lambda r: (r["start"], r["end"], r["title"]))
    return rebuilt


def _score_plan(rows: List[Dict[str, Any]], original_rows: List[Dict[str, Any]], origin: Optional[str], default_mode: Optional[str]) -> Tuple[int, int, int, int]:
    time_pen = len(_time_conflicts(rows))
    travel_pen = len(_travel_conflicts(rows, origin, default_mode))
    move_pen = 0
    early_pen = 0
    orig_map = {(r["kind"], _normalize_title(r["title"]).lower(), str(r.get("location") or "").lower()): r for r in original_rows}
    for row in rows:
        key = (row["kind"], _normalize_title(row["title"]).lower(), str(row.get("location") or "").lower())
        orig = orig_map.get(key)
        if orig:
            move_pen += abs(int(row["start"]) - int(orig["start"]))
        if int(row["start"]) < 8 * 60:
            early_pen += (8 * 60 - int(row["start"]))
    return (time_pen, travel_pen, early_pen, move_pen)


def _rebuild_candidates(rows: List[Dict[str, Any]], origin: Optional[str], default_mode: Optional[str]) -> List[Dict[str, Any]]:
    base = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    cands = []

    # preserve current order
    rebuilt_a = _simulate_from_order(base, origin, default_mode, start_min=DAY_START)
    cands.append({"label": "zachowaj kolejność", "rows": rebuilt_a})

    # start from 08:00 for more human day
    rebuilt_b = _simulate_from_order(base, origin, default_mode, start_min=8 * 60)
    cands.append({"label": "zacznij dzień o 08:00", "rows": rebuilt_b})

    # move later items first by giving preference to already-later events
    later_sorted = sorted(base, key=lambda r: (r["start"] < 8*60, r["start"], r["title"]))
    rebuilt_c = _simulate_from_order(later_sorted, origin, default_mode, start_min=8 * 60)
    cands.append({"label": "preferuj godziny dzienne", "rows": rebuilt_c})

    for cand in cands:
        cand["score"] = _score_plan(cand["rows"], base, origin, default_mode)
    cands.sort(key=lambda c: c["score"])
    return cands


def global_day_rebuilder(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "AI DAY REBUILDER"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Brak punktów na ten dzień.")
        return "\n".join(lines)

    current_time = _time_conflicts(rows)
    current_travel = _travel_conflicts(rows, origin, default_mode)
    if current_time:
        lines.append("Obecne konflikty czasowe:")
        lines.extend(f"• {x}" for x in current_time)
        lines.append("")
    if current_travel:
        lines.append("Obecne konflikty logistyczne:")
        lines.extend(f"• {x}" for x in current_travel)
        lines.append("")

    cands = _rebuild_candidates(rows, origin, default_mode)
    if not cands:
        lines.append("Nie udało się zbudować wariantów.")
        return "\n".join(lines)

    lines.append("Najlepsze warianty przebudowy dnia:")
    for idx, cand in enumerate(cands[:3], start=1):
        start_line = f"{idx}. {cand['label']}"
        if cand["rows"]:
            start_line += f" — start od {_fmt_hhmm(cand['rows'][0]['start'])}"
        lines.append(start_line)
    lines.extend([
        "",
        "Możesz teraz wpisać:",
        "• `przebuduj jutro automatycznie`",
        "• `ai day rebuilder jutro`",
    ])
    return "\n".join(lines)


def apply_day_rebuild(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "APPLY AI DAY REBUILD"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Brak punktów na ten dzień.")
        return "\n".join(lines)

    cands = _rebuild_candidates(rows, origin, default_mode)
    if not cands:
        lines.append("Nie udało się zbudować wariantów.")
        return "\n".join(lines)

    best = cands[0]
    moved = []
    for old, new in zip(sorted(rows, key=lambda r: (r["start"], r["end"], r["title"])), best["rows"]):
        old_time = _fmt_hhmm(old["start"])
        new_time = _fmt_hhmm(new["start"])
        if old["kind"] == "event" and old_time != new_time:
            ok = _save_event_move(target, old["title"], old_time, new_time)
            if ok:
                moved.append(f"• `{old['title']}`: {old_time} → {new_time}")

    final_time = _time_conflicts(best["rows"])
    final_travel = _travel_conflicts(best["rows"], origin, default_mode)

    if moved:
        lines.append("Wprowadzone zmiany:")
        lines.extend(moved)
        lines.append("")
    else:
        lines.append("Nie było zmian do zapisania.")
        lines.append("")

    lines.append("Walidacja po przebudowie:")
    if not final_time and not final_travel:
        lines.append("✅ Dzień po przebudowie nie ma konfliktów czasowych ani logistycznych.")
    else:
        if final_time:
            lines.append("⚠️ Nadal widzę konflikty czasowe:")
            lines.extend(f"• {x}" for x in final_time[:8])
        if final_travel:
            lines.append("⚠️ Nadal widzę konflikty logistyczne:")
            lines.extend(f"• {x}" for x in final_travel[:8])
    return "\n".join(lines)
