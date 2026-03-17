
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EVENTS_FILE = Path("data/memory/events.json")


def _ensure_dir() -> None:
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _read_events_raw() -> List[Dict[str, Any]]:
    if not EVENTS_FILE.exists():
        return []
    try:
        data = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_events(items: List[Dict[str, Any]]) -> None:
    _ensure_dir()
    EVENTS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_title(title: str) -> str:
    t = (title or "").strip(" ,.")
    low = t.lower()
    replacements = {
        "do dentysty": "dentysta",
        "dentystę": "dentysta",
        "dentyste": "dentysta",
        "na spotkanie": "spotkanie",
        "na trening": "trening",
        "rozmowę o pracę": "rozmowa o pracę",
        "rozmowe o prace": "rozmowa o pracę",
    }
    for src, dst in replacements.items():
        if low.startswith(src):
            t = dst + t[len(src):]
            break
    return re.sub(r"\s+", " ", t).strip()


def _normalize_key(title: str, due_date: str, due_time: str, location: Optional[str]) -> Tuple[str, str, str, str]:
    return (
        _normalize_title(title).lower(),
        str(due_date or "").strip(),
        str(due_time or "").strip(),
        str(location or "").strip().lower(),
    )


def _to_min(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _fmt_hhmm(minutes: int) -> str:
    minutes = max(0, int(minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _smart_merge_events(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Smart dedup:
    - exact duplicates: title+date+time+location
    - likely duplicates: same normalized title + same date + within 90 min
      keep richer item (location wins), otherwise keep earlier time
    """
    normalized: List[Dict[str, Any]] = []
    exact_seen = set()
    removed = 0

    for item in items:
        key = _normalize_key(
            str(item.get("title") or ""),
            str(item.get("date") or ""),
            str(item.get("time") or ""),
            str(item.get("location") or ""),
        )
        if key in exact_seen:
            removed += 1
            continue
        exact_seen.add(key)
        norm = dict(item)
        norm["title"] = _normalize_title(str(norm.get("title") or ""))
        normalized.append(norm)

    normalized.sort(key=lambda x: (str(x.get("date") or ""), str(x.get("time") or ""), int(x.get("id") or 0)))

    merged: List[Dict[str, Any]] = []
    for item in normalized:
        title = _normalize_title(str(item.get("title") or "")).lower()
        d = str(item.get("date") or "")
        t = str(item.get("time") or "")
        if not d or not t:
            merged.append(item)
            continue

        current_min = _to_min(t)
        found_idx = None
        for idx, existing in enumerate(merged):
            ex_title = _normalize_title(str(existing.get("title") or "")).lower()
            ex_date = str(existing.get("date") or "")
            ex_time = str(existing.get("time") or "")
            if ex_title != title or ex_date != d or not ex_time:
                continue
            if abs(_to_min(ex_time) - current_min) <= 90:
                found_idx = idx
                break

        if found_idx is None:
            merged.append(item)
            continue

        existing = merged[found_idx]
        existing_loc = str(existing.get("location") or "").strip()
        current_loc = str(item.get("location") or "").strip()

        # choose richer record; if same richness keep earlier time
        choose_current = False
        if current_loc and not existing_loc:
            choose_current = True
        elif len(current_loc) > len(existing_loc):
            choose_current = True
        elif current_min < _to_min(str(existing.get("time") or "23:59")):
            choose_current = True

        if choose_current:
            merged[found_idx] = item
        removed += 1

    merged.sort(key=lambda x: (str(x.get("date") or ""), str(x.get("time") or ""), int(x.get("id") or 0)))
    return merged, removed


def _load_events() -> List[Dict[str, Any]]:
    items, removed = _smart_merge_events(_read_events_raw())
    _save_events(items)
    return items


def smart_dedup_events() -> str:
    raw = _read_events_raw()
    cleaned, removed = _smart_merge_events(raw)
    _save_events(cleaned)
    lines = ["SMART DEDUP", ""]
    lines.append(f"Usunięte/scalone wpisy: {removed}")
    lines.append(f"Pozostałe wydarzenia: {len(cleaned)}")
    if cleaned:
        lines.append("")
        for ev in cleaned[:12]:
            row = f"• {ev.get('date')} {ev.get('time')} — {ev.get('title')}"
            if ev.get("location"):
                row += f" ({ev.get('location')})"
            lines.append(row)
    return "\n".join(lines)


def _norm_hhmm(raw: str) -> str:
    raw = (raw or "").strip()
    if ":" in raw:
        hh, mm = raw.split(":", 1)
        return f"{int(hh):02d}:{int(mm):02d}"
    return f"{int(raw):02d}:00"


def _day_to_date(word: str) -> str:
    w = (word or "").strip().lower()
    if w == "jutro":
        return (date.today() + timedelta(days=1)).isoformat()
    return date.today().isoformat()


def _split_title_location(text: str) -> tuple[str, Optional[str]]:
    txt = (text or "").strip(" ,.")
    if "," in txt:
        a, b = txt.split(",", 1)
        return a.strip(), b.strip() or None
    for marker in [" przy ", " na ", " w "]:
        if marker in txt:
            a, b = txt.split(marker, 1)
            if a.strip() and b.strip():
                return a.strip(), marker.strip() + " " + b.strip()
    return txt, None


def _find_duplicate(items: List[Dict[str, Any]], title: str, due_date: str, due_time: str, location: Optional[str]) -> Optional[Dict[str, Any]]:
    key = _normalize_key(title, due_date, due_time, location)
    for item in items:
        if _normalize_key(
            str(item.get("title") or ""),
            str(item.get("date") or ""),
            str(item.get("time") or ""),
            str(item.get("location") or ""),
        ) == key:
            return item
    return None


def _collect_task_blocks(date_iso: str) -> List[Tuple[str, int, int]]:
    try:
        from app.b2c import tasks as tasks_mod
        tasks = tasks_mod.list_tasks_for_date(date_iso) or []
    except Exception:
        return []
    out = []
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
        title = str(t.get("title") or t.get("text") or "zadanie").strip()
        out.append((title, start, start + duration))
    return out


def _collect_event_blocks(date_iso: str, existing: List[Dict[str, Any]]) -> List[Tuple[str, int, int]]:
    out = []
    for e in existing:
        if str(e.get("date") or "") != date_iso:
            continue
        time_s = str(e.get("time") or "")
        if not time_s:
            continue
        try:
            start = _to_min(time_s)
        except Exception:
            continue
        out.append((str(e.get("title") or "wydarzenie"), start, start + 60))
    return out


def _find_time_conflicts(title: str, due_date: str, due_time: str, existing_events: List[Dict[str, Any]]) -> List[str]:
    try:
        start = _to_min(due_time)
    except Exception:
        return []
    end = start + 60
    conflicts: List[str] = []
    for other_title, other_start, other_end in _collect_event_blocks(due_date, existing_events) + _collect_task_blocks(due_date):
        if other_end > start and other_start < end:
            conflicts.append(other_title)
    uniq = []
    for x in conflicts:
        if x not in uniq and _normalize_title(x).lower() != _normalize_title(title).lower():
            uniq.append(x)
    return uniq[:5]


def _add_event(title: str, due_date: str, due_time: str, location: Optional[str] = None) -> tuple[Dict[str, Any], bool, List[str]]:
    items = _load_events()
    duplicate = _find_duplicate(items, title, due_date, due_time, location)
    if duplicate is not None:
        return duplicate, False, []

    conflicts = _find_time_conflicts(title, due_date, due_time, items)
    event_id = max([int(x.get("id", 0)) for x in items], default=0) + 1
    item = {"id": event_id, "title": _normalize_title(title), "date": due_date, "time": due_time, "location": location or ""}
    items.append(item)
    items, _ = _smart_merge_events(items)
    _save_events(items)
    return item, True, conflicts


def event_brain_summary() -> str:
    items = _load_events()
    today = date.today().isoformat()
    upcoming = [x for x in items if str(x.get("date") or "") >= today]
    lines = ["EVENT BRAIN", "", f"Wydarzenia: {len(upcoming)}"]
    if not upcoming:
        lines.append("Brak zapisanych wydarzeń.")
        return "\n".join(lines)
    lines.append("")
    for ev in upcoming[:12]:
        row = f"• {ev.get('date')} {ev.get('time')} — {ev.get('title')}"
        if ev.get("location"):
            row += f" ({ev.get('location')})"
        lines.append(row)
    return "\n".join(lines)


def today_events() -> str:
    items = _load_events()
    today = date.today().isoformat()
    rows = [x for x in items if str(x.get("date") or "") == today]
    lines = [f"WYDARZENIA DNIA — {today}", ""]
    if not rows:
        lines.append("Brak wydarzeń na dziś.")
        return "\n".join(lines)
    for ev in rows:
        row = f"• {ev.get('time')} — {ev.get('title')}"
        if ev.get("location"):
            row += f" ({ev.get('location')})"
        lines.append(row)
    return "\n".join(lines)


def maybe_handle_event_nlp(message: str) -> Optional[Dict[str, str]]:
    raw = (message or "").strip()
    low = raw.lower()
    event_markers = (
        "dentyst", "spotkani", "rozmow", "obiad", "kolacj", "trening",
        "wizyta", "demo", "kalendarz", "wydarzen", "lekarz", "rozmowę", "rozmowe"
    )
    if not any(m in low for m in event_markers) and not re.search(r"\b(jutro|dziś|dzis|dzisiaj)\b", low):
        return None

    patterns = [
        r"^(?:mam|muszę|musze|jest|będzie|bedzie)?\s*(?P<rest>.+?)\s+(?P<day>jutro|dziś|dzis|dzisiaj)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)$",
        r"^(?:mam|muszę|musze)?\s*(?P<day>jutro|dziś|dzis|dzisiaj)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<rest>.+)$",
        r"^(?P<day>jutro|dziś|dzis|dzisiaj)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<rest>.+)$",
        r"^(?P<rest>.+?)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<day>jutro|dziś|dzis|dzisiaj)$",
    ]
    for pat in patterns:
        m = re.match(pat, raw, flags=re.I)
        if not m:
            continue
        due_date = _day_to_date(m.group("day"))
        due_time = _norm_hhmm(m.group("time"))
        title, location = _split_title_location(_normalize_title(m.group("rest")))
        if title:
            ev, created, conflicts = _add_event(title, due_date, due_time, location)
            if created:
                msg = f"📅 Dodałam wydarzenie: {ev['title']} ({ev['date']} {ev['time']})"
                if ev.get("location"):
                    msg += f" • {ev['location']}"
                if conflicts:
                    msg += "\n⚠️ Możliwy konflikt czasowy z: " + ", ".join(conflicts)
                    try:
                        from app.b2c.v36_1_brain import remember_conflict
                        remember_conflict(ev['title'], ev['date'], ev['time'], conflicts)
                        msg += "\n💡 Wpisz `rozwiąż konflikt`, żeby zobaczyć opcje."
                    except Exception:
                        pass
            else:
                msg = f"ℹ️ To wydarzenie już istnieje: {ev['title']} ({ev['date']} {ev['time']})"
                if ev.get("location"):
                    msg += f" • {ev['location']}"
            return {"intent": "event_add", "reply": msg}
    return None
