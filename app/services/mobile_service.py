
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.intent.router import route_intent, tasks_mod, _get_origin_address, _get_place


CATEGORY_PRIORITY = {
    "zdrowie": 1,
    "kariera": 1,
    "praca": 2,
    "administracja": 2,
    "dom": 3,
    "zakupy": 4,
    "inne": 5,
}


def _to_min(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _fmt_hhmm(minutes: int) -> str:
    minutes = max(0, int(minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _classify_title(title: str) -> str:
    low = (title or "").strip().lower()
    if any(x in low for x in ["dentyst", "lekarz", "badanie", "wizyta", "zdrow"]):
        return "zdrowie"
    if any(x in low for x in ["rozmowa o prac", "rekrut", "cv", "karier", "oferta pracy"]):
        return "kariera"
    if any(x in low for x in ["spotkanie", "call", "meeting", "projekt", "prezentacja"]):
        return "praca"
    if any(x in low for x in ["urząd", "urzad", "bank", "opłata", "oplata", "rachunek", "podatek"]):
        return "administracja"
    if any(x in low for x in ["sprząt", "sprzat", "dom", "napraw", "pranie"]):
        return "dom"
    if any(x in low for x in ["zakupy", "sklep", "kupi", "apteka"]):
        return "zakupy"
    return "inne"


def _event_rows(target_date: str) -> List[Dict[str, Any]]:
    try:
        from app.b2c.v34_brain import _load_events
        items = _load_events()
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for idx, e in enumerate(items, start=1):
        if str(e.get("date") or "") != target_date:
            continue
        t = str(e.get("time") or "")
        if not t:
            continue
        try:
            start = _to_min(t)
        except Exception:
            continue
        title = str(e.get("title") or "wydarzenie")
        category = _classify_title(title)
        rows.append({
            "id": f"event-{idx}",
            "kind": "event",
            "title": title,
            "start_min": start,
            "end_min": start + 60,
            "start": t,
            "end": _fmt_hhmm(start + 60),
            "location": str(e.get("location") or "").strip() or None,
            "category": category,
            "priority": CATEGORY_PRIORITY.get(category, 5),
        })
    return rows


def _task_rows(target_date: str) -> List[Dict[str, Any]]:
    try:
        tasks = tasks_mod.list_tasks_for_date(target_date) or []
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for idx, t in enumerate(tasks, start=1):
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
        title = str(t.get("title") or t.get("text") or "zadanie").strip()
        category = _classify_title(title)
        rows.append({
            "id": f"task-{idx}",
            "kind": "task",
            "title": title,
            "start_min": start,
            "end_min": start + duration,
            "start": time_s,
            "end": _fmt_hhmm(start + duration),
            "location": str(t.get("location") or "").strip() or None,
            "category": category,
            "priority": CATEGORY_PRIORITY.get(category, 5),
        })
    return rows


def _free_windows(rows: List[Dict[str, Any]], day_start: int = 8 * 60, day_end: int = 20 * 60) -> List[Dict[str, str]]:
    ordered = sorted(rows, key=lambda r: (r["start_min"], r["end_min"], r["title"]))
    if not ordered:
        return [{"start": _fmt_hhmm(day_start), "end": _fmt_hhmm(day_end)}]
    out: List[Dict[str, str]] = []
    cur = day_start
    for row in ordered:
        if row["start_min"] > cur:
            out.append({"start": _fmt_hhmm(cur), "end": _fmt_hhmm(row["start_min"])})
        cur = max(cur, row["end_min"])
    if cur < day_end:
        out.append({"start": _fmt_hhmm(cur), "end": _fmt_hhmm(day_end)})
    return out


def _time_blocks(free_windows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    blocks: List[Dict[str, str]] = []
    lunch_added = False
    for win in free_windows:
        s = _to_min(win["start"])
        e = _to_min(win["end"])
        if not lunch_added:
            lunch_start = max(s, 12 * 60)
            lunch_end = min(e, 14 * 60)
            if lunch_end - lunch_start >= 30:
                blocks.append({"start": _fmt_hhmm(lunch_start), "end": _fmt_hhmm(lunch_start + 30), "label": "lunch"})
                lunch_added = True
        if e - s >= 45:
            focus_end = min(e, s + 90)
            blocks.append({"start": _fmt_hhmm(s), "end": _fmt_hhmm(focus_end), "label": "focus"})
    return blocks[:6]


def _priorities(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    base = []
    for row in rows:
        if row["kind"] not in {"event", "task"}:
            continue
        base.append({
            "title": row["title"],
            "category": row.get("category") or "inne",
            "priority": int(row.get("priority") or 5),
            "time": row["start"],
            "kind": row["kind"],
        })
    base.sort(key=lambda x: (x["priority"], x.get("time") or "99:99", x["title"]))
    return base


def build_day_payload(day_offset: int = 0) -> Dict[str, Any]:
    target = (date.today() + timedelta(days=day_offset)).isoformat()
    rows = _event_rows(target) + _task_rows(target)
    rows.sort(key=lambda r: (r["start_min"], r["end_min"], r["title"]))

    free_windows = _free_windows(rows)
    blocks = _time_blocks(free_windows)
    priorities = _priorities(rows)

    summary = {"status": "empty", "next_item": None, "next_time": None}
    if rows:
        summary = {
            "status": "ok",
            "next_item": rows[0]["title"],
            "next_time": rows[0]["start"],
        }

    timeline = []
    for row in rows:
        timeline.append({
            "id": row["id"],
            "kind": row["kind"],
            "title": row["title"],
            "start": row["start"],
            "end": row["end"],
            "location": row.get("location"),
            "category": row.get("category"),
            "priority": row.get("priority"),
        })

    for idx, block in enumerate(blocks, start=1):
        timeline.append({
            "id": f"block-{idx}",
            "kind": block["label"],
            "title": "Lunch" if block["label"] == "lunch" else "Focus",
            "start": block["start"],
            "end": block["end"],
            "location": None,
            "category": None,
            "priority": None,
        })
    timeline.sort(key=lambda r: (r["start"], r["end"], r["title"]))

    return {
        "date": target,
        "summary": summary,
        "timeline": timeline,
        "free_windows": free_windows,
        "time_blocks": blocks,
        "priorities": priorities,
    }


def create_inbox_item(text: str) -> Dict[str, Any]:
    out = route_intent(text, persona="b2c", mode="b2c")
    return {
        "status": "ok",
        "intent": str(out.get("intent") or ""),
        "message": str(out.get("reply") or out.get("response") or "OK"),
        "changed": True,
    }


def plan_tomorrow() -> Dict[str, Any]:
    out = route_intent("zaplanuj jutro", persona="b2c", mode="b2c")
    msg = str(out.get("reply") or out.get("response") or "Plan jutra został zaktualizowany.")
    return {
        "status": "ok",
        "intent": str(out.get("intent") or "plan_tomorrow"),
        "message": msg,
        "changed": True,
    }


def get_memory() -> Dict[str, Any]:
    try:
        out = route_intent("co o mnie wiesz", persona="b2c", mode="b2c")
        return {
            "status": "ok",
            "message": str(out.get("reply") or out.get("response") or ""),
        }
    except Exception:
        return {"status": "ok", "message": ""}


def get_priorities_tomorrow() -> Dict[str, Any]:
    payload = build_day_payload(day_offset=1)
    return {
        "status": "ok",
        "date": payload["date"],
        "priorities": payload["priorities"],
    }


def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "product": "Jarvis Mobile API",
        "version": "v1",
    }
