
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

DAY_START = 6 * 60
DAY_END = 22 * 60
PREFERRED_START = 8 * 60
PREFERRED_END = 20 * 60


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
    rows: List[Dict[str, Any]] = []
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
    rows: List[Dict[str, Any]] = []
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


def _normalize_title(title: str) -> str:
    try:
        from app.b2c.v34_brain import _normalize_title
        return _normalize_title(title)
    except Exception:
        return str(title or "").strip()


def _move_event(date_iso: str, title: str, old_time: str, new_time: str) -> bool:
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


def _time_conflicts(rows: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    risks: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        if a["end"] > b["start"]:
            risks.append((a, b))
    return risks


def _travel_need(prev_loc: Optional[str], row: Dict[str, Any], default_mode: Optional[str], buffer_min: int) -> Optional[Tuple[int, int]]:
    loc = str(row.get("location") or "").strip()
    if not prev_loc or not loc:
        return None
    eta = _eta_minutes(prev_loc, loc, row.get("travel_mode") or default_mode)
    if eta is None:
        return None
    leave = row["start"] - eta - buffer_min
    return eta, leave


def _travel_conflicts(rows: List[Dict[str, Any]], origin: Optional[str], default_mode: Optional[str], buffer_min: int) -> List[Tuple[Dict[str, Any], int, int]]:
    ordered = sorted(rows, key=lambda r: (r["start"], r["end"], r["title"]))
    risks: List[Tuple[Dict[str, Any], int, int]] = []
    prev_end = None
    prev_loc = origin
    for row in ordered:
        need = _travel_need(prev_loc, row, default_mode, buffer_min)
        if prev_end is not None and need is not None:
            eta, leave = need
            if leave < prev_end:
                risks.append((row, eta, leave))
        prev_end = row["end"]
        prev_loc = str(row.get("location") or "").strip() or prev_loc
    return risks


def _simulate_rows_with_move(rows: List[Dict[str, Any]], target_row: Dict[str, Any], new_start: int) -> List[Dict[str, Any]]:
    duration = int(target_row["end"] - target_row["start"])
    out: List[Dict[str, Any]] = []
    for row in rows:
        nr = dict(row)
        if row is target_row:
            nr["start"] = new_start
            nr["end"] = new_start + duration
            nr["time"] = _fmt_hhmm(new_start)
        out.append(nr)
    out.sort(key=lambda r: (r["start"], r["end"], r["title"]))
    return out


def _unified_issues(rows: List[Dict[str, Any]], origin: Optional[str], default_mode: Optional[str], buffer_min: int) -> Tuple[List[str], List[str]]:
    time_issues = [
        f"{_fmt_hhmm(a['start'])} {a['title']} ↔ {_fmt_hhmm(b['start'])} {b['title']}"
        for a, b in _time_conflicts(rows)
    ]
    travel_issues = [
        f"`{row['title']}` wymaga wyjścia o {_fmt_hhmm(leave)} (ETA {eta} min)."
        for row, eta, leave in _travel_conflicts(rows, origin, default_mode, buffer_min)
    ]
    return time_issues[:8], travel_issues[:8]


def _rank_slot(candidate: int, original_start: int, conflict_start: int) -> Tuple[int, int, int, int]:
    """
    Human-friendly ranking:
    1) prefer slots after the conflicting block
    2) then prefer smallest distance from original
    3) prefer daytime (08:00-20:00)
    4) avoid very early hours
    """
    after_conflict_penalty = 0 if candidate >= conflict_start else 1
    distance_penalty = abs(candidate - original_start)
    daytime_penalty = 0 if PREFERRED_START <= candidate <= PREFERRED_END else 1
    early_penalty = 1 if candidate < PREFERRED_START else 0
    return (after_conflict_penalty, daytime_penalty, early_penalty, distance_penalty)


def _safe_slot_candidates(rows: List[Dict[str, Any]], target_row: Dict[str, Any], origin: Optional[str], default_mode: Optional[str], buffer_min: int) -> List[int]:
    duration = int(target_row["end"] - target_row["start"])
    valid: List[int] = []
    for cand in range(DAY_START, DAY_END - duration + 1, 5):
        simulated = _simulate_rows_with_move(rows, target_row, cand)
        time_issues, travel_issues = _unified_issues(simulated, origin, default_mode, buffer_min)
        if not time_issues and not travel_issues:
            valid.append(cand)

    conflict_start = target_row["start"]
    valid.sort(key=lambda c: _rank_slot(c, target_row["start"], conflict_start))
    return valid


def auto_travel_planner(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0, buffer_min: int = 10) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "HUMAN SCHEDULER"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Brak punktów na ten dzień.")
        return "\n".join(lines)

    time_issues, travel_issues = _unified_issues(rows, origin, default_mode, buffer_min)
    if not time_issues and not travel_issues:
        lines.append("Nie widzę konfliktów czasowych ani logistycznych. Plan wygląda stabilnie.")
        return "\n".join(lines)

    if time_issues:
        lines.append("Wykryte konflikty czasowe:")
        lines.extend(f"• {x}" for x in time_issues)
        lines.append("")
    if travel_issues:
        lines.append("Wykryte konflikty logistyczne:")
        lines.extend(f"• {x}" for x in travel_issues)
        lines.append("")

    lines.append("Proponowane naprawy:")
    candidate_rows: List[Dict[str, Any]] = [row for row, _, _ in _travel_conflicts(rows, origin, default_mode, buffer_min)]
    if not candidate_rows:
        seen = set()
        for a, b in _time_conflicts(rows):
            for row in (b, a):
                key = (row["title"], row["start"], row["kind"])
                if key not in seen:
                    seen.add(key)
                    candidate_rows.append(row)

    shown = 0
    used_titles = set()
    for row in candidate_rows:
        key = (row["title"], row["start"], row["kind"])
        if key in used_titles:
            continue
        used_titles.add(key)
        safe_slots = [s for s in _safe_slot_candidates(rows, row, origin, default_mode, buffer_min) if s != row["start"]]
        if safe_slots:
            lines.append(f"• Przesuń `{row['title']}` z {_fmt_hhmm(row['start'])} na {_fmt_hhmm(safe_slots[0])}.")
            if len(safe_slots) > 1:
                lines.append(f"  Alternatywa: {_fmt_hhmm(safe_slots[1])}.")
        else:
            lines.append(f"• Nie widzę bezpiecznego slotu dla `{row['title']}`. Rozważ ręczne przełożenie lub zmianę trybu dojazdu.")
        shown += 1
        if shown >= 6:
            break

    lines.extend([
        "",
        "Możesz teraz wpisać:",
        "• `auto travel planner jutro`",
        "• `napraw logistykę jutra automatycznie`",
    ])
    return "\n".join(lines)


def auto_repair_travel_plan(tasks_mod, origin: Optional[str], default_mode: Optional[str], day_offset: int = 0, buffer_min: int = 10) -> str:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(tasks_mod, target)
    rows.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    title = "HUMAN SAFE AUTO REPAIR TRAVEL PLAN"
    if day_offset == 1:
        title += " — JUTRO"
    lines = [f"{title} — {target}", ""]

    if not rows:
        lines.append("Nie mam nic do naprawy.")
        return "\n".join(lines)

    initial_time, initial_travel = _unified_issues(rows, origin, default_mode, buffer_min)
    if not initial_time and not initial_travel:
        lines.append("Nie widzę konfliktów czasowych ani logistycznych. Plan wygląda stabilnie.")
        return "\n".join(lines)

    moved: List[str] = []
    manual: List[str] = []
    working_rows = list(rows)

    candidate_rows: List[Dict[str, Any]] = [row for row, _, _ in _travel_conflicts(working_rows, origin, default_mode, buffer_min)]
    if not candidate_rows:
        seen = set()
        for a, b in _time_conflicts(working_rows):
            key = (b["title"], b["start"], b["kind"])
            if key not in seen:
                seen.add(key)
                candidate_rows.append(b)

    processed = set()
    for row in candidate_rows:
        rkey = (row["title"], row["start"], row["kind"])
        if rkey in processed:
            continue
        processed.add(rkey)

        safe_slots = [s for s in _safe_slot_candidates(working_rows, row, origin, default_mode, buffer_min) if s != row["start"]]
        if not safe_slots:
            manual.append(f"• `{row['title']}` — brak bezpiecznego slotu. Rozważ ręczne przełożenie.")
            continue

        new_start = safe_slots[0]
        old_time = _fmt_hhmm(row["start"])
        new_time = _fmt_hhmm(new_start)

        if row["kind"] != "event":
            manual.append(f"• `{row['title']}` — auto-przesuwanie tasków nie jest jeszcze włączone. Proponowany slot: {new_time}.")
            continue

        simulated = _simulate_rows_with_move(working_rows, row, new_start)
        sim_time, sim_travel = _unified_issues(simulated, origin, default_mode, buffer_min)
        if sim_time or sim_travel:
            manual.append(f"• `{row['title']}` — znaleziony slot {new_time} nadal nie jest bezpieczny.")
            continue

        if _move_event(target, row["title"], old_time, new_time):
            moved.append(f"• Przesunęłam `{row['title']}` z {old_time} na {new_time}.")
            working_rows = simulated
        else:
            manual.append(f"• `{row['title']}` — nie udało się zapisać zmiany na {new_time}.")

    final_time, final_travel = _unified_issues(working_rows, origin, default_mode, buffer_min)

    if moved:
        lines.append("Wprowadzone zmiany:")
        lines.extend(moved)
    if manual:
        if moved:
            lines.append("")
        lines.append("Rzeczy do ręcznej decyzji:")
        lines.extend(manual)

    if not moved and not manual:
        lines.append("Nie udało się nic bezpiecznie zmienić.")
        return "\n".join(lines)

    lines.extend(["", "Walidacja po zmianach:"])
    if not final_time and not final_travel:
        lines.append("✅ Plan po naprawie nie ma konfliktów czasowych ani logistycznych.")
    else:
        if final_time:
            lines.append("⚠️ Nadal widzę konflikty czasowe:")
            lines.extend(f"• {x}" for x in final_time[:8])
        if final_travel:
            lines.append("⚠️ Nadal widzę konflikty logistyczne:")
            lines.extend(f"• {x}" for x in final_travel[:8])
    return "\n".join(lines)
