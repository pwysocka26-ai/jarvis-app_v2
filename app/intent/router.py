# ROUTER_BUILD: late_pred_A_buf10
from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple
import os
import re
import math
from datetime import date, datetime, timedelta

from app.b2c import tasks as tasks_mod
from app.b2c.travel_mode import morning_brief
from app.b2c.maps_google import get_eta_minutes


# Travel configuration (MVP)
TRAVEL_BUFFER_MIN = 10  # safety buffer (minutes)

YES = {"tak", "t", "yes", "y", "ok", "jasne", "pewnie"}
NO = {"nie", "n", "no"}


def _clean_title_for_display(title: str) -> str:
    """Make task titles user-friendly (defensive cleanup)."""
    t = (title or "").strip()
    # strip accidental command prefixes that might leak into title
    t = re.sub(r"^\s*[-•]*\s*(dodaj|add)\s*:?\s*", "", t, flags=re.IGNORECASE)
    return t.strip()

# Wersja A: emoji (działa wszędzie)
PRIORITY_EMOJI = {
    1: "🔴",  # p1
    2: "🟠",  # p2
    3: "🟢",  # p3
}


WEEKDAY_MAP = {
    "poniedziałek": 0, "poniedzialek": 0,
    "wtorek": 1,
    "środa": 2, "sroda": 2, "środę": 2, "srodę": 2,
    "czwartek": 3,
    "piątek": 4, "piatek": 4, "piątku": 4, "piatku": 4,
    "sobota": 5, "sobotę": 5, "sobote": 5,
    "niedziela": 6, "niedzielę": 6, "niedziele": 6,
}


def _normalize_hhmm_token(tok: str) -> Optional[str]:
    s = (tok or '').strip()
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?$', s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2) or '00')
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return f"{hh:02d}:{mm:02d}"


def _next_weekday_date(name: str) -> Optional[date]:
    wd = WEEKDAY_MAP.get((name or '').strip().lower())
    if wd is None:
        return None
    today = date.today()
    delta = (wd - today.weekday()) % 7
    if delta == 0:
        delta = 7
    return today + timedelta(days=delta)


def _split_title_and_location(rest: str) -> Tuple[str, Optional[str]]:
    s = (rest or '').strip().strip(',')
    if not s:
        return '', None
    if ',' in s:
        title, loc = s.split(',', 1)
        return title.strip(), loc.strip() or None
    return s, None


def _parse_checklist_items(items_raw: str) -> List[str]:
    out: List[str] = []
    for part in re.split(r',|;|\n', items_raw or ''):
        item = str(part).strip().lstrip('-').strip()
        if item:
            out.append(item)
    return out


def _looks_like_new_task_request(message: str) -> bool:
    msg = (message or '').strip()
    low = msg.lower()
    if not msg:
        return False
    if low.startswith('dodaj:') or low.startswith('add:'):
        return True
    if re.match(r'^za\s+(?:(?:\d+)\s*(?:min|minut(?:y)?|m|h)|(?:1\s*)?godzin(?:ę|e|y|a)?)\s+.+$', low, flags=re.I):
        return True
    if re.match(r'^(?:dziś|dzisiaj|jutro)\s+\d{1,2}(?::\d{2})?\s+.+$', msg, flags=re.I):
        return True
    if re.match(r'^.+\s+(?:dziś|dzisiaj|jutro)\s+\d{1,2}(?::\d{2})?(?:\s*,\s*.+)?$', msg, flags=re.I):
        return True
    if re.match(r'^w\s+(?:poniedzia[łl]ek|wtorek|[śs]rod[ęea]|czwartek|pi[ąa]tek|sobot[ęea]|niedziel[ęea])\s+\d{1,2}(?::\d{2})?\s+.+$', msg, flags=re.I):
        return True
    if ':' in msg and len(_parse_checklist_items(msg.rsplit(':', 1)[1])) >= 2:
        return True
    return False


def _build_add_message(title: str, due_date: date, due_time: str, location: Optional[str] = None) -> str:
    base = f"dodaj: {due_date.isoformat()} {due_time} {title.strip()}"
    if location:
        base += f", {location.strip()}"
    return base


def _create_task_from_nlp(title: str, due_date: date, due_time: str, location: Optional[str] = None, checklist: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    synthetic = _build_add_message(title=title, due_date=due_date, due_time=due_time, location=location)
    out = tasks_mod.add_task(synthetic)
    task = out.get('task') if isinstance(out, dict) else None
    if isinstance(task, dict) and checklist and hasattr(tasks_mod, 'update_task'):
        try:
            tasks_mod.update_task(int(task.get('id')), checklist=checklist)
            task = tasks_mod.get_task(int(task.get('id'))) or task
            out['task'] = task
        except Exception:
            pass
    return out


def _maybe_handle_stable_nlp(message: str) -> Optional[Dict[str, Any]]:
    msg = (message or '').strip()
    low = msg.lower()

    # Relative time: 'za 30 minut telefon', 'za godzinę telefon', 'za 2h telefon'
    m_rel = re.match(r'^za\s+(?:(\d+)\s*(?:min|minut(?:y)?|m)|(?:1\s*)?(godzin(?:ę|e|y|a)?|h)|(?:(\d+)\s*h))\s+(.+)$', low, flags=re.I)
    if m_rel:
        mins = None
        if m_rel.group(1):
            mins = int(m_rel.group(1))
        elif m_rel.group(2):
            mins = 60
        elif m_rel.group(3):
            mins = int(m_rel.group(3)) * 60
        title_part = msg[m_rel.start(4):].strip()
        if mins and title_part:
            due_dt = datetime.now() + timedelta(minutes=mins)
            out = _create_task_from_nlp(title=title_part, due_date=due_dt.date(), due_time=due_dt.strftime('%H:%M'))
            return _as_reply('add_task', _reply_from_any(out, 'OK'))

    # Checklist task with time / place: 'zrób zakupy o 15:00 w Biedronce przy Narbutta: mleko, chleb'
    if ':' in msg:
        head, items_raw = msg.rsplit(':', 1)
        items = _parse_checklist_items(items_raw)
        if items:
            head = head.strip()
            title = None
            due_date = date.today()
            due_time = None
            location = None
            patterns = [
                r'^(?P<title>.+?)\s+(?P<day>dziś|dzisiaj|jutro)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)\s+w\s+(?P<loc>.+)$',
                r'^(?P<title>.+?)\s+(?P<day>dziś|dzisiaj|jutro)\s+(?P<time>\d{1,2}(?::\d{2})?)\s+w\s+(?P<loc>.+)$',
                r'^(?P<title>.+?)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)\s+w\s+(?P<loc>.+)$',
                r'^(?P<title>.+?)\s+w\s+(?P<loc>.+?)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)$',
                r'^(?P<title>.+?)\s+(?P<day>dziś|dzisiaj|jutro)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)$',
                r'^(?P<title>.+?)\s+o\s+(?P<time>\d{1,2}(?::\d{2})?)$',
            ]
            for pat in patterns:
                m = re.match(pat, head, flags=re.I)
                if not m:
                    continue
                title = m.group('title').strip()
                if m.groupdict().get('day'):
                    day = m.group('day').lower()
                    due_date = date.today() + timedelta(days=1) if day == 'jutro' else date.today()
                due_time = _normalize_hhmm_token(m.group('time'))
                location = (m.groupdict().get('loc') or '').strip() or None
                break
            if title and due_time:
                title = re.sub(r'^zrobi[ćc]\s+', '', title, flags=re.I).strip()
                if re.match(r'^(zakupy|zrob\s+zakupy)$', title, flags=re.I):
                    title = 'zakupy'
                checklist = {'title': title.capitalize() if title else 'Lista', 'items': [{'text': it, 'done': False} for it in items]}
                out = _create_task_from_nlp(title=title, due_date=due_date, due_time=due_time, location=location, checklist=checklist)
                return _as_reply('add_task', _reply_from_any(out, 'OK'))

    # 'jutro 9 dentysta' / 'dziś 18:30 dentysta, adres'
    m_prefix = re.match(r'^(?P<day>dziś|dzisiaj|jutro)\s+(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<rest>.+)$', msg, flags=re.I)
    if m_prefix:
        due_date = date.today() + timedelta(days=1) if m_prefix.group('day').lower() == 'jutro' else date.today()
        due_time = _normalize_hhmm_token(m_prefix.group('time'))
        title, location = _split_title_and_location(m_prefix.group('rest'))
        if title and due_time:
            out = _create_task_from_nlp(title=title, due_date=due_date, due_time=due_time, location=location)
            return _as_reply('add_task', _reply_from_any(out, 'OK'))

    # 'dentysta dziś 18:30'
    m_suffix = re.match(r'^(?P<rest>.+?)\s+(?P<day>dziś|dzisiaj|jutro)\s+(?P<time>\d{1,2}(?::\d{2})?)$', msg, flags=re.I)
    if m_suffix:
        due_date = date.today() + timedelta(days=1) if m_suffix.group('day').lower() == 'jutro' else date.today()
        due_time = _normalize_hhmm_token(m_suffix.group('time'))
        title, location = _split_title_and_location(m_suffix.group('rest'))
        if title and due_time:
            out = _create_task_from_nlp(title=title, due_date=due_date, due_time=due_time, location=location)
            return _as_reply('add_task', _reply_from_any(out, 'OK'))

    # 'w środę 14 demo'
    m_weekday = re.match(r'^w\s+(?P<weekday>poniedziałek|poniedzialek|wtorek|środę|srodę|środa|sroda|czwartek|piątek|piatek|sobotę|sobote|sobota|niedzielę|niedziele|niedziela)\s+(?P<time>\d{1,2}(?::\d{2})?)\s+(?P<rest>.+)$', msg, flags=re.I)
    if m_weekday:
        due_date = _next_weekday_date(m_weekday.group('weekday'))
        due_time = _normalize_hhmm_token(m_weekday.group('time'))
        title, location = _split_title_and_location(m_weekday.group('rest'))
        if due_date and due_time and title:
            out = _create_task_from_nlp(title=title, due_date=due_date, due_time=due_time, location=location)
            return _as_reply('add_task', _reply_from_any(out, 'OK'))

    return None


def _task_time_str(t: Dict[str, Any]) -> str:
    """Return HH:MM if task has a concrete due time."""
    v = t.get("time")
    if isinstance(v, str) and v.strip():
        return v.strip()
    due_at = t.get("due_at")
    if isinstance(due_at, str) and "T" in due_at and len(due_at) >= 16:
        return due_at.split("T", 1)[1][:5]
    return ""

SORT_PRIORITY = "priority"
SORT_TIME = "time"

ORIGIN_HOME = "dom"
ORIGIN_WORK = "praca"
ORIGIN_CURRENT = "tu"
ORIGIN_CUSTOM = "custom"


def _as_reply(intent: str, reply: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = {"intent": intent, "reply": reply, "response": reply}
    if extra:
        out.update(extra)
    return out


def _reply_from_any(out: Any, default: str = "OK") -> str:
    if isinstance(out, dict):
        return str(out.get("reply") or out.get("response") or default)
    if out is True:
        return default
    if out is False or out is None:
        return "Nie udało się."
    return str(out)


# -----------------------------
# Tasks DB settings (persisted)
# -----------------------------
def _load_db() -> Dict[str, Any]:
    # Prefer new API if present
    if hasattr(tasks_mod, "load_tasks_db"):
        return tasks_mod.load_tasks_db()  # type: ignore[attr-defined]
    # Fallback: try older storage
    if hasattr(tasks_mod, "load_tasks"):
        return {"tasks": tasks_mod.load_tasks()}  # type: ignore[attr-defined]
    return {}


def _save_db(db: Dict[str, Any]) -> bool:
    if hasattr(tasks_mod, "save_tasks_db"):
        tasks_mod.save_tasks_db(db)  # type: ignore[attr-defined]
        return True
    return False


def _get_settings() -> Dict[str, Any]:
    db = _load_db()
    s = db.get("settings")
    return s if isinstance(s, dict) else {}


def _set_settings(settings: Dict[str, Any]) -> bool:
    db = _load_db()
    db["settings"] = settings
    return _save_db(db)


def _get_sort_mode() -> str:
    mode = _get_settings().get("sort_mode")
    return mode if mode in {SORT_PRIORITY, SORT_TIME} else SORT_TIME


def _set_sort_mode(mode: str) -> bool:
    if mode not in {SORT_PRIORITY, SORT_TIME}:
        return False
    s = _get_settings()
    s["sort_mode"] = mode
    return _set_settings(s)


def _get_origin_mode() -> str:
    mode = _get_settings().get("origin_mode")
    return mode if mode in {ORIGIN_HOME, ORIGIN_WORK, ORIGIN_CURRENT} else ORIGIN_HOME


def _set_origin_mode(mode: str) -> bool:
    if mode not in {ORIGIN_HOME, ORIGIN_WORK, ORIGIN_CURRENT}:
        return False
    s = _get_settings()
    s["origin_mode"] = mode
    return _set_settings(s)


def _set_place(key: str, value: str) -> bool:
    s = _get_settings()
    s[key] = value
    # stamp last update for current location
    if key == "origin_current":
        s["origin_current_updated_at"] = datetime.now().isoformat(timespec="seconds")
    return _set_settings(s)


def _get_place(key: str) -> Optional[str]:
    v = _get_settings().get(key)
    return str(v).strip() if isinstance(v, str) and v.strip() else None


def _get_origin_address() -> Optional[str]:
    """Resolve origin based on selected origin_mode, with fallback:
    tu -> dom -> praca
    dom -> dom
    praca -> praca
    """
    mode = _get_origin_mode()
    if mode == ORIGIN_CURRENT:
        cur = _get_place("origin_current")
        if cur:
            return cur
        # fallback
        home = _get_place("origin_home")
        if home:
            return home
        return _get_place("origin_work")

    if mode == ORIGIN_WORK:
        work = _get_place("origin_work")
        if work:
            return work
        return _get_place("origin_home")

    # ORIGIN_HOME
    home = _get_place("origin_home")
    if home:
        return home
    return _get_place("origin_work")




def _resolve_origin_from_answer(ans: str) -> Tuple[str, Optional[str]]:
    raw = (ans or "").strip()
    low = raw.lower()
    if low in {"dom", "home"}:
        return ORIGIN_HOME, _get_place("origin_home")
    if low in {"praca", "work"}:
        return ORIGIN_WORK, _get_place("origin_work")
    if low in {"tu", "tutaj", "obecna", "obecna lokalizacja"}:
        return ORIGIN_CURRENT, _get_place("origin_current") or _get_place("origin_home") or _get_place("origin_work")
    return ORIGIN_CUSTOM, raw

# -----------------------------
# Sorting & display helpers
# -----------------------------
def _parse_time_to_minutes(t: Optional[str]) -> Optional[int]:
    if not t:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", str(t).strip())
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return hh * 60 + mm


def _parse_created_at(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts))
    except Exception:
        return None


def _sort_for_list(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort used by list/delete and LIVE numbering.

    Single source of truth lives in app.b2c.tasks.sort_for_list.
    """
    mode = _get_sort_mode()
    try:
        return tasks_mod.sort_for_list(tasks or [], mode=mode)
    except Exception:
        return tasks or []



def _label_for_date(d: date) -> str:
    if d == date.today():
        return "dziś"
    if d == date.today() + timedelta(days=1):
        return "jutro"
    return d.isoformat()


def _parse_date_arg(arg: str) -> Optional[date]:
    if arg in {"dziś", "dzis", "dzisiaj"}:
        return date.today()
    if arg == "jutro":
        return date.today() + timedelta(days=1)
    try:
        return date.fromisoformat(arg)
    except Exception:
        return None


def _extract_date_and_index(parts: List[str], default_date: date) -> Optional[Tuple[date, int]]:
    if len(parts) == 2:
        try:
            return (default_date, int(parts[1]))
        except Exception:
            return None
    if len(parts) >= 3:
        d = _parse_date_arg(parts[1])
        if d is None:
            return None
        try:
            return (d, int(parts[2]))
        except Exception:
            return None
    return None


WEEKDAY_MAP = {
    "poniedzialek": 0,
    "poniedziałek": 0,
    "wtorek": 1,
    "sroda": 2,
    "środa": 2,
    "srode": 2,
    "środę": 2,
    "czwartek": 3,
    "piatek": 4,
    "piątek": 4,
    "sobota": 5,
    "sobote": 5,
    "sobotę": 5,
    "niedziela": 6,
    "niedziele": 6,
    "niedzielę": 6,
}


def _next_weekday_date(name: str) -> Optional[date]:
    target = WEEKDAY_MAP.get((name or "").strip().lower())
    if target is None:
        return None
    today = date.today()
    delta = (target - today.weekday()) % 7
    if delta == 0:
        delta = 7
    return today + timedelta(days=delta)


def _fmt_time(hh: int, mm: int = 0) -> str:
    return f"{int(hh):02d}:{int(mm):02d}"


def _build_nlp_add_command(message: str) -> Optional[str]:
    """Translate short natural Polish task phrases into stable `dodaj:` commands.

    v11.1 fix: allow phrases starting with today words (e.g. `dziś 18:30 dentysta, adres`)
    and keep the full tail, including address text after commas.
    """
    raw = (message or "").strip()
    if not raw:
        return None

    low = raw.lower().strip()
    blocked_prefixes = (
        "/", "dodaj", "lista", "usun", "usuń", "priorytet", "sort", "ustaw",
        "tu jestem", "start:", "rano", "diag", "help", "pamiec", "pamięć",
        "pokaz", "pokaż", "co pamietasz", "co pamiętasz", "zapamietaj",
        "zapamiętaj", "zapomnij", "gdzie ", "plan dnia",
        "pomys", "notatk", "reminders", "inbox", "eta",
        "czy zdaz", "czy zdąż", "przenies", "przenieś", "edytuj", "wyczysc", "wyczyść",
        "ułóż dzień", "uloz dzien", "przeplanuj", "ile mam wolnego czasu", "reset",
    )
    # Do not block natural task phrases that start with "dziś/dzisiaj".
    # Exact commands like "dziś" are still handled later by the router.
    if low in YES or low in NO or low.startswith(blocked_prefixes) or low in {"dziś", "dzis", "dzisiaj", "co dziś", "co dzis"}:
        return None

    m = re.match(r"^za\s+(\d+)\s*(h|godz|godzin(?:e|ę|y)?|m|min|mins|minut(?:e|ę|y)?)\s+(.+)$", low, flags=re.I)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        title = raw[m.start(3):].strip(' ,')
        now = datetime.now().replace(second=0, microsecond=0)
        if unit.startswith('h') or unit.startswith('godz') or 'godzin' in unit:
            target = now + timedelta(hours=amount)
        else:
            target = now + timedelta(minutes=amount)
        return f"dodaj: {target.date().isoformat()} {_fmt_time(target.hour, target.minute)} {title}"

    m = re.match(r"^za\s+godzin(?:e|ę)?\s+(.+)$", low, flags=re.I)
    if m:
        title = raw[m.start(1):].strip(' ,')
        target = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
        return f"dodaj: {target.date().isoformat()} {_fmt_time(target.hour, target.minute)} {title}"

    m = re.match(r"^(?:w\s+)?(poniedziałek|poniedzialek|wtorek|środa|sroda|środę|srode|czwartek|piątek|piatek|sobota|sobotę|sobote|niedziela|niedzielę|niedziele)(?:\s+o)?\s+(\d{1,2})(?::(\d{2}))?\s+(.+)$", raw, flags=re.I)
    if m:
        target_date = _next_weekday_date(m.group(1))
        if target_date:
            hh = int(m.group(2))
            mm = int(m.group(3) or 0)
            title = m.group(4).strip(' ,')
            return f"dodaj: {target_date.isoformat()} {_fmt_time(hh, mm)} {title}"

    m = re.match(r"^(?:w\s+)?(poniedziałek|poniedzialek|wtorek|środa|sroda|środę|srode|czwartek|piątek|piatek|sobota|sobotę|sobote|niedziela|niedzielę|niedziele)\s+(.+)$", raw, flags=re.I)
    if m:
        target_date = _next_weekday_date(m.group(1))
        if target_date:
            title = m.group(2).strip(' ,')
            return f"dodaj: {target_date.isoformat()} {title}"

    m = re.match(r"^(dziś|dzis|jutro)(?:\s+o)?\s+(\d{1,2})(?::(\d{2}))?\s+(.+)$", raw, flags=re.I)
    if m:
        day_word = m.group(1).lower()
        hh = int(m.group(2))
        mm = int(m.group(3) or 0)
        title = m.group(4).strip(' ,')
        return f"dodaj: {day_word} {_fmt_time(hh, mm)} {title}"

    m = re.match(r"^(.+?)\s+(dziś|dzis|jutro)(?:\s+o)?\s+(\d{1,2})(?::(\d{2}))?$", raw, flags=re.I)
    if m:
        title = m.group(1).strip(' ,')
        day_word = m.group(2).lower()
        hh = int(m.group(3))
        mm = int(m.group(4) or 0)
        return f"dodaj: {day_word} {_fmt_time(hh, mm)} {title}"

    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s+(.+)$", raw, flags=re.I)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
        title = m.group(3).strip(' ,')
        if 0 <= hh <= 23 and 0 <= mm <= 59 and len(title) >= 2:
            return f"dodaj: dziś {_fmt_time(hh, mm)} {title}"

    return None


def _priority_emoji(priority: Any, explicit: bool = True) -> str:
    try:
        pr = int(priority)
    except Exception:
        return ""
    if pr == 2 and not explicit:
        return ""
    return PRIORITY_EMOJI.get(pr, f"p{pr} ") if pr in PRIORITY_EMOJI else (f"p{pr} " if pr else "")



def _normalize_travel_mode(s: str) -> Optional[str]:
    t = (s or "").strip().lower()
    t = t.replace("ą","a").replace("ę","e").replace("ł","l").replace("ó","o").replace("ś","s").replace("ć","c").replace("ń","n").replace("ż","z").replace("ź","z")
    # allow variants
    if t in {"samochod", "samochodem", "auto", "car", "driving"}:
        return "samochod"
    if t in {"autobus", "komunikacja", "komunikacja_miejska", "komunikacja miejska", "komunikacja", "komunikacja", "transit", "bus"}:
        return "autobus"
    if t in {"rower", "rowerem", "bike", "biking"}:
        return "rower"
    if t in {"pieszo", "pieszo.", "spacer", "walk", "walking"}:
        return "pieszo"
    return None


def _mvp_eta_minutes(travel_mode: str) -> int:
    mode = _normalize_travel_mode(travel_mode) or "samochod"
    return {"samochod": 25, "autobus": 40, "rower": 18, "pieszo": 60}.get(mode, 25)


def _google_mode_from_task(travel_mode: str) -> Optional[str]:
    tm = (travel_mode or "").lower()
    # cover Polish variants
    if tm in {"samochód", "samochodem", "auto", "car", "driving"}:
        return "driving"
    if tm in {"komunikacja", "komunikacją", "zbiorkom", "transit", "bus", "metro", "tram"}:
        return "transit"
    if tm in {"rower", "rowerem", "bike", "bicycle", "bicycling"}:
        return "bicycling"
    if tm in {"pieszo", "spacer", "walk", "walking"}:
        return "walking"
    return None


def _display_mode_label(travel_mode: str) -> str:
    tm = _normalize_travel_mode(travel_mode) or "samochod"
    return {"samochod": "samochodem", "autobus": "komunikacją", "rower": "rowerem", "pieszo": "pieszo"}.get(tm, "samochodem")


def _task_title(task: Dict[str, Any]) -> str:
    return _clean_title_for_display(str(task.get("title") or task.get("text") or "(bez tytułu)")).strip()


def _task_location(task: Dict[str, Any]) -> str:
    return str(task.get("location") or task.get("place") or "").strip()


def _task_priority(task: Dict[str, Any]) -> int:
    try:
        return int(task.get("priority") or 2)
    except Exception:
        return 2


def _task_due_minutes(task: Dict[str, Any]) -> Optional[int]:
    return _parse_time_to_minutes(_task_time_str(task))


def _brain_eta_for_task(task: Dict[str, Any], origin: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    location = _task_location(task)
    if not (origin and location):
        return None, None
    raw_mode = str(task.get("travel_mode") or _get_place("travel_mode_default") or "samochod")
    gm = _google_mode_from_task(raw_mode)
    minutes = None
    if gm:
        try:
            minutes = get_eta_minutes(origin=origin, destination=location, mode=gm)
        except Exception:
            minutes = None
    if not (isinstance(minutes, int) and minutes > 0):
        minutes = _mvp_eta_minutes(raw_mode)
    return int(minutes), _display_mode_label(raw_mode)


def _brain_rank_key(task: Dict[str, Any]) -> Tuple[int, int, int, str]:
    pr = _task_priority(task)
    due_min = _task_due_minutes(task)
    has_time = 0 if due_min is not None else 1
    return (pr, has_time, due_min if due_min is not None else 9999, str(task.get("created_at") or ""))


def _brain_today_tasks() -> List[Dict[str, Any]]:
    tasks = _sort_for_list(tasks_mod.list_tasks_for_date(date.today()) or [])
    return [t for t in tasks if isinstance(t, dict) and not bool(t.get("done"))]


def _brain_choose_next(tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not tasks:
        return None
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    overdue_timed = [t for t in tasks if _task_due_minutes(t) is not None and (_task_due_minutes(t) or 0) < now_min]
    if overdue_timed:
        return sorted(overdue_timed, key=lambda t: ((_task_due_minutes(t) or 0), _task_priority(t)))[0]
    upcoming_timed = [t for t in tasks if _task_due_minutes(t) is not None and (_task_due_minutes(t) or 0) >= now_min]
    if upcoming_timed:
        return sorted(upcoming_timed, key=lambda t: ((_task_due_minutes(t) or 9999), _task_priority(t)))[0]
    return sorted(tasks, key=_brain_rank_key)[0]


def _brain_now_reply(tasks: List[Dict[str, Any]]) -> str:
    if not tasks:
        return "Na dziś nie masz żadnych otwartych zadań. Możesz dodać coś nowego albo zajrzeć do pomysłów."
    chosen = _brain_choose_next(tasks)
    if not chosen:
        return "Na dziś nie widzę nic pilnego."
    title = _task_title(chosen)
    location = _task_location(chosen)
    due_min = _task_due_minutes(chosen)
    pr = _task_priority(chosen)
    pr_txt = f"p{pr}" if pr else "p2"
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    origin = _get_origin_address()
    if due_min is not None:
        when = f"{due_min // 60:02d}:{due_min % 60:02d}"
        if location and origin:
            eta_min, mode_label = _brain_eta_for_task(chosen, origin)
            if eta_min is not None:
                leave_min = due_min - eta_min - TRAVEL_BUFFER_MIN
                if now_min >= leave_min:
                    return (
                        f"Teraz zrób to: **wyjdź na {title}**.\n"
                        f"Godzina: **{when}**\n"
                        f"Trasa: {origin} → {location}\n"
                        f"ETA: około **{eta_min} min** ({mode_label})\n"
                        f"Bufor: {TRAVEL_BUFFER_MIN} min."
                    )
                mins_left = leave_min - now_min
                return (
                    f"Teraz najlepiej przygotuj się do: **{title}**.\n"
                    f"Start: **{when}**\n"
                    f"Wyjście za około **{mins_left} min**.\n"
                    f"Trasa: {origin} → {location}\n"
                    f"ETA: około **{eta_min} min** ({mode_label})."
                )
        if due_min - now_min <= 30:
            return f"Teraz najlepiej zajmij się: **{title}**. Zaczyna się o **{when}**."
        return f"Teraz najbliższe zadanie to: **{title}** o **{when}** ({pr_txt})."
    top_timed = [t for t in tasks if _task_due_minutes(t) is not None]
    nearest_timed_gap = ((_task_due_minutes(top_timed[0]) or 9999) - now_min) if top_timed else 9999
    if pr == 1 and nearest_timed_gap > 45:
        return f"Teraz zrób: **{title}**. To Twoje najwyższe priorytetowo zadanie na dziś ({pr_txt})."
    return f"Teraz dobry moment na: **{title}** ({pr_txt})."


def _brain_next_reply(tasks: List[Dict[str, Any]]) -> str:
    chosen = _brain_choose_next(tasks)
    if not chosen:
        return "Na dziś nie masz już żadnych zadań."
    title = _task_title(chosen)
    location = _task_location(chosen)
    due_min = _task_due_minutes(chosen)
    pr = _task_priority(chosen)
    pr_txt = f"p{pr}" if pr else "p2"
    if due_min is not None:
        when = f"{due_min // 60:02d}:{due_min % 60:02d}"
        tail = f" — {location}" if location else ""
        return f"Następne zadanie: **{when} {title}**{tail} ({pr_txt})."
    return f"Następne zadanie bez godziny: **{title}** ({pr_txt})."


def _brain_top_reply(tasks: List[Dict[str, Any]]) -> str:
    if not tasks:
        return "Na dziś nie masz jeszcze żadnych zadań."
    ranked = sorted(tasks, key=_brain_rank_key)[:3]
    lines = ["**Najważniejsze dziś:**"]
    for idx, task in enumerate(ranked, start=1):
        title = _task_title(task)
        pr = _task_priority(task)
        due_min = _task_due_minutes(task)
        when = f"{due_min // 60:02d}:{due_min % 60:02d} — " if due_min is not None else ""
        loc = _task_location(task)
        tail = f" — {loc}" if loc else ""
        lines.append(f"{idx}. {when}{title}{tail} (p{pr})")
    return "\n".join(lines)


def route_intent(message: str, persona: str = "b2c", mode: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    low = (message or "").strip().lower()


    if low in {"wyczyść wszystko", "wyczysc wszystko", "reset wszystko", "reset all", "/reset_all"}:
        try:
            from app.b2c import inbox as inbox_mod
            for path in [tasks_mod.TASKS_FILE, inbox_mod.INBOX_FILE, inbox_mod.IDEAS_FILE, inbox_mod.NOTES_FILE, inbox_mod.REMINDERS_FILE]:
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("[]", encoding="utf-8")
                except Exception:
                    pass
            for fn_name in ("clear_pending_travel", "clear_pending_reminder", "clear_pending_checklist", "clear_pending_clear"):
                try:
                    fn = getattr(tasks_mod, fn_name, None)
                    if fn:
                        fn()
                except Exception:
                    pass
            return _as_reply("reset_all", "🧹 Wyczyściłam dane testowe Jarvisa.\nTasks: 0\nIdeas: 0\nNotes: 0\nReminders: 0\nInbox: 0\n\n(Zachowałam ustawienia: dom / praca / tryb).")
        except Exception:
            return _as_reply("reset_all", "Nie udało się wyczyścić wszystkich danych.")

    if low in {
        "co powinienem zrobić teraz", "co powinienem zrobic teraz",
        "co mam zrobić teraz", "co mam zrobic teraz",
        "co teraz", "co robić teraz", "co robic teraz"
    }:
        return _as_reply("brain_now", _brain_now_reply(_brain_today_tasks()))

    if low in {"następne zadanie", "nastepne zadanie", "co dalej", "następny krok", "nastepny krok"}:
        return _as_reply("brain_next", _brain_next_reply(_brain_today_tasks()))

    if low in {
        "co jest dziś najważniejsze", "co jest dzis najwazniejsze",
        "najważniejsze dziś", "najwazniejsze dzis",
        "priorytety dnia"
    }:
        return _as_reply("brain_top", _brain_top_reply(_brain_today_tasks()))

    if low in {"czy zdążę na wszystkie zadania", "czy zdaze na wszystkie zadania", "czy zdążę na wszystko", "czy zdaze na wszystko"}:
        try:
            from app.b2c.context_ai import assess_all_today_schedule
            return _as_reply("context_all_fit", assess_all_today_schedule(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("context_all_fit", "Nie mogę teraz sprawdzić całego planu dnia.")

    if low in {"co mogę zrobić w wolnym czasie", "co moge zrobic w wolnym czasie", "co w wolnym czasie", "wolny czas co robić", "wolny czas co robic"}:
        try:
            from app.b2c.context_ai import suggest_for_free_time
            return _as_reply("context_free_time", suggest_for_free_time(tasks_mod))
        except Exception:
            return _as_reply("context_free_time", "Nie mogę teraz podpowiedzieć co zrobić w wolnym czasie.")

    if low in {"przełóż mniej ważne zadania", "przeloz mniej wazne zadania", "przełóż mniej ważne", "przeloz mniej wazne"}:
        try:
            from app.b2c.context_ai import postpone_lower_priority_tasks
            return _as_reply("context_postpone", postpone_lower_priority_tasks(tasks_mod))
        except Exception:
            return _as_reply("context_postpone", "Nie mogę teraz przełożyć mniej ważnych zadań.")

    if low in {"zaplanuj mi dzień automatycznie", "zaplanuj mi dzien automatycznie", "ułóż mi dzień automatycznie", "uloz mi dzien automatycznie"}:
        try:
            from app.b2c.context_ai import auto_plan_day
            return _as_reply("context_autoplan", auto_plan_day(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("context_autoplan", "Nie mogę teraz automatycznie zaplanować dnia.")

    if low in {"zaplanuj cały mój dzień", "zaplanuj caly moj dzien", "zaplanuj cały dzień", "zaplanuj caly dzien", "zaplanuj mój dzień", "zaplanuj moj dzien", "autoplan dnia", "ułóż dzień automatycznie", "uloz dzien automatycznie"}:
        try:
            from app.b2c.context_ai import plan_whole_day
            return _as_reply("context_plan_whole_day", plan_whole_day(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("context_plan_whole_day", "Nie mogę teraz zaplanować całego dnia.")

    m_now_window = re.match(r'^co mog[eę]\s+zrobi[cć]\s+teraz\s+w\s+(\d{1,3})\s+min(?:ut(?:y)?)?$', low)
    if m_now_window:
        try:
            from app.b2c.context_ai import suggest_now_with_limit
            minutes = int(m_now_window.group(1))
            return _as_reply("context_now_window", suggest_now_with_limit(tasks_mod, minutes))
        except Exception:
            return _as_reply("context_now_window", "Nie mogę teraz podpowiedzieć co zmieści się w tym oknie.")

    if low in {"zoptymalizuj plan dnia", "optymalizuj plan dnia", "ulepsz plan dnia"}:
        try:
            from app.b2c.context_ai import optimize_day_plan
            return _as_reply("context_optimize_day", optimize_day_plan(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("context_optimize_day", "Nie mogę teraz zoptymalizować planu dnia.")

    if low in {"przygotuj mnie do następnego zadania", "przygotuj mnie do nastepnego zadania", "przygotuj do następnego zadania", "przygotuj do nastepnego zadania"}:
        try:
            from app.b2c.context_ai import prepare_for_next_task
            return _as_reply("context_prepare_next", prepare_for_next_task(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("context_prepare_next", "Nie mogę teraz przygotować Cię do następnego zadania.")


    if low in {"jaki jest mój następny krok", "jaki jest moj nastepny krok", "mój następny krok", "moj nastepny krok", "co dalej dziś", "co dalej dzis"}:
        try:
            from app.b2c.context_ai import daily_next_step
            return _as_reply("daily_next_step", daily_next_step(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("daily_next_step", "Nie mogę teraz wskazać następnego kroku.")

    if low in {"przygotuj mój dzień", "przygotuj moj dzien", "przygotuj dzien", "rozpocznij dzień", "rozpocznij dzien"}:
        try:
            from app.b2c.context_ai import prepare_my_day
            return _as_reply("daily_prepare_day", prepare_my_day(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("daily_prepare_day", "Nie mogę teraz przygotować Twojego dnia.")

    if low in {"co mogę zrobić w tym oknie czasu", "co moge zrobic w tym oknie czasu", "co mogę zrobić w tym oknie", "co moge zrobic w tym oknie", "co zmieści się w tym oknie", "co zmiesci sie w tym oknie"}:
        try:
            from app.b2c.context_ai import suggest_for_current_window
            return _as_reply("daily_window", suggest_for_current_window(tasks_mod, _get_origin_address(), _get_place("travel_mode_default") or "samochod", buffer_min=TRAVEL_BUFFER_MIN))
        except Exception:
            return _as_reply("daily_window", "Nie mogę teraz ocenić tego okna czasu.")
    # =============================
    # INBOX v1
    # =============================
    if low.startswith("zapisz:"):
        from app.b2c import inbox as inbox_mod
        text = message.split(":", 1)[1].strip()
        out = inbox_mod.add_inbox(text)
        return _as_reply("inbox_add", out.get("reply", "OK"))

    if low == "inbox":
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.list_inbox()
        return _as_reply("inbox_list", out.get("reply", "Inbox jest pusty."))

    if low.startswith("usuń z inbox") or low.startswith("usun z inbox"):
        from app.b2c import inbox as inbox_mod
        m = re.search(r"(\d+)$", low)
        if not m:
            return _as_reply("inbox_delete", "Użyj: `usuń z inbox 1`.")
        out = inbox_mod.delete_inbox_by_live_number(int(m.group(1)))
        return _as_reply("inbox_delete", out.get("reply", "OK"))

    if low in {"/reset_inbox", "wyczyść inbox", "wyczysc inbox"}:
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.clear_inbox()
        return _as_reply("inbox_clear", out.get("reply", "OK"))

    m_inbox_to_task = re.match(r"^zamie[nń]\s+inbox\s+(\d+)\s+na\s+zadanie\s+(.+)$", message, flags=re.I)
    if m_inbox_to_task:
        from app.b2c import inbox as inbox_mod
        n = int(m_inbox_to_task.group(1))
        suffix = m_inbox_to_task.group(2).strip()
        item = inbox_mod.get_inbox_by_live_number(n)
        if not item:
            return _as_reply("inbox_to_task", f"Nie ma wpisu #{n} w Inbox.")
        synthetic = f"dodaj: {item['text']} {suffix}".strip()
        out = tasks_mod.add_task(synthetic)
        if isinstance(out, dict) and out.get("task"):
            inbox_mod.delete_inbox_by_live_number(n)
        return _as_reply("inbox_to_task", _reply_from_any(out, default="OK"))

    # ===== INBOX v7 BUCKETS =====
    if low in {"pomysły", "pomysly", "pomysł", "pomysl"}:
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.list_bucket(inbox_mod.IDEAS_FILE, "Pomysły")
        return _as_reply("ideas_list", out.get("reply", "Pomysły są puste."))

    if low in {"notatki", "notatka"}:
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.list_bucket(inbox_mod.NOTES_FILE, "Notatki")
        return _as_reply("notes_list", out.get("reply", "Notatki są puste."))

    if low in {"reminders", "reminder"}:
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.list_bucket(inbox_mod.REMINDERS_FILE, "Reminders")
        return _as_reply("reminders_list", out.get("reply", "Reminders są puste."))

    m_bucket_clear = re.match(r"^(?:usu[ńn]\s+wszystko\s+z\s+|wyczy[śs]?[ćc]?\s+)(pomys(?:ł|l)(?:y|ów|ow)?|notatk(?:i|ę|e|ek)|reminders?)\s*$", message, flags=re.I)
    if m_bucket_clear:
        from app.b2c import inbox as inbox_mod
        kind_raw = m_bucket_clear.group(1).lower()
        kind = "idea" if kind_raw.startswith("pomys") else "note" if kind_raw.startswith("notatk") else "reminder"
        out = inbox_mod.clear_bucket(kind)
        return _as_reply("bucket_clear", out.get("reply", "OK"))

    m_bucket_move_all = re.match(r"^przenie[śs]\s+wszystko\s+z\s+(pomys(?:ł|l)ów|notatek|reminders?)\s+do\s+zada[ńn](?:\s+(.+))?$", message, flags=re.I)
    if m_bucket_move_all:
        from app.b2c import inbox as inbox_mod
        kind_raw = m_bucket_move_all.group(1).lower()
        kind = "idea" if kind_raw.startswith("pomys") else "note" if kind_raw.startswith("notat") else "reminder"
        suffix = (m_bucket_move_all.group(2) or "").strip()
        out = inbox_mod.move_all_bucket_to_task(kind, suffix)
        return _as_reply("bucket_to_task_all", out.get("reply", "OK"))

    m_bucket_delete = re.match(r"^usu[ńn]\s+(pomys[łl]|notatk[ęe]|reminder)\s+(\d+)\s*$", message, flags=re.I)
    if m_bucket_delete:
        from app.b2c import inbox as inbox_mod
        kind_raw = m_bucket_delete.group(1).lower()
        kind = "idea" if kind_raw.startswith("pomys") else "note" if kind_raw.startswith("notatk") else "reminder"
        out = inbox_mod.delete_bucket_item(kind, int(m_bucket_delete.group(2)))
        return _as_reply("bucket_delete", out.get("reply", "OK"))

    m_bucket_edit = re.match(r"^edytuj\s+(pomys[łl]|notatk[ęe]|reminder)\s+(\d+)\s+(.+)$", message, flags=re.I)
    if m_bucket_edit:
        from app.b2c import inbox as inbox_mod
        kind_raw = m_bucket_edit.group(1).lower()
        kind = "idea" if kind_raw.startswith("pomys") else "note" if kind_raw.startswith("notatk") else "reminder"
        out = inbox_mod.edit_bucket_item(kind, int(m_bucket_edit.group(2)), m_bucket_edit.group(3).strip())
        return _as_reply("bucket_edit", out.get("reply", "OK"))

    m_bucket_move = re.match(r"^przenie[śs]\s+(pomys[łl]|notatk[ęe]|reminder)\s+(\d+)\s+do\s+zadania(?:\s+(.+))?$", message, flags=re.I)
    if m_bucket_move:
        from app.b2c import inbox as inbox_mod
        kind_raw = m_bucket_move.group(1).lower()
        kind = "idea" if kind_raw.startswith("pomys") else "note" if kind_raw.startswith("notatk") else "reminder"
        suffix = (m_bucket_move.group(3) or "").strip()
        out = inbox_mod.move_bucket_item_to_task(kind, int(m_bucket_move.group(2)), suffix)
        return _as_reply("bucket_to_task", out.get("reply", "OK"))


    def _is_command_like(txt: str) -> bool:
        t = (txt or "").strip().lower()
        return (
            t.startswith("/")
            or t.startswith("lista")
            or t.startswith("dodaj")
            or t.startswith("usun")
            or t.startswith("usuń")
            or t.startswith("priorytet")
            or t.startswith("sort")
            or t.startswith("ustaw")
            or t.startswith("tu jestem")
            or t.startswith("start:")
            or t.startswith("rano")
            or t.startswith("diag")
            or t.startswith("help")
            or t.startswith("pamięć")
            or t.startswith("pamiec")
            or t.startswith("pokaż pamięć")
            or t.startswith("pokaz pamiec")
            or t.startswith("co pamiętasz")
            or t.startswith("co pamietasz")
            or t.startswith("zapamiętaj")
            or t.startswith("zapamietaj")
            or t.startswith("zapomnij")
            or t.startswith("gdzie ")
            or t.startswith("plan dnia")
            or t.startswith("co mogę zrobić w wolnym czasie")
            or t.startswith("co moge zrobic w wolnym czasie")
            or t.startswith("czy zdążę na wszystkie zadania")
            or t.startswith("czy zdaze na wszystkie zadania")
            or t.startswith("przełóż mniej ważne zadania")
            or t.startswith("przeloz mniej wazne zadania")
            or t.startswith("zaplanuj mi dzień automatycznie")
            or t.startswith("zaplanuj cały mój dzień")
            or t.startswith("co mogę zrobić teraz w")
            or t.startswith("zoptymalizuj plan dnia")
            or t.startswith("przygotuj mnie do następnego zadania")
            or t.startswith("zaplanuj mi dzien automatycznie")
            or t.startswith("co dziś")
            or t.startswith("co dzis")
            or t.startswith("dzisiaj")
            or t.startswith("dziś")
        )

    # =============================
    # ORIGIN settings
    # =============================
    if low.startswith("ustaw dom:"):
        addr = message.split(":", 1)[1].strip()
        ok = _set_place("origin_home", addr)
        return _as_reply("set_origin_home", "✅ Ustawiono dom." if ok else "Nie udało się ustawić domu.")

    if low.startswith("ustaw praca:") or low.startswith("ustaw pracę:") or low.startswith("ustaw prace:"):
        addr = message.split(":", 1)[1].strip()
        ok = _set_place("origin_work", addr)
        return _as_reply("set_origin_work", "✅ Ustawiono pracę." if ok else "Nie udało się ustawić pracy.")

    if low.startswith("tu jestem:"):
        addr = message.split(":", 1)[1].strip()
        ok = _set_place("origin_current", addr)
        return _as_reply("set_origin_current", "✅ OK, zapamiętałem gdzie jesteś." if ok else "Nie udało się zapisać lokalizacji.")

    # =============================
    # SMART PLAN / V10
    # =============================
    if low in {"ułóż dzień", "uloz dzien", "ułoz dzien", "ułóż dzien"}:
        try:
            from app.b2c.smart_plan import build_smart_day_plan
            today_iso = date.today().isoformat()
            tasks_today = tasks_mod.list_tasks_for_date(today_iso) or []
            origin_addr = _get_origin_address()
            transport_default = _get_place("travel_mode_default") or "samochod"
            plan = build_smart_day_plan(tasks_today, today_iso, origin_addr, transport_default, buffer_min=TRAVEL_BUFFER_MIN)
            return _as_reply("smart_day_plan", plan)
        except Exception:
            return _as_reply("smart_day_plan", "Nie mogę teraz ułożyć dnia.")

    if low in {"przeplanuj dzień", "przeplanuj dzien"}:
        try:
            from app.b2c.smart_plan import build_replanned_day_plan
            today_iso = date.today().isoformat()
            tasks_today = tasks_mod.list_tasks_for_date(today_iso) or []
            origin_addr = _get_origin_address()
            transport_default = _get_place("travel_mode_default") or "samochod"
            plan = build_replanned_day_plan(tasks_today, today_iso, origin_addr, transport_default, buffer_min=TRAVEL_BUFFER_MIN)
            return _as_reply("smart_day_plan", plan)
        except Exception:
            return _as_reply("smart_day_plan", "Nie mogę teraz przeplanować dnia.")

    if low in {"ile mam wolnego czasu", "wolny czas", "ile wolnego czasu"}:
        try:
            from app.b2c.smart_plan import summarize_free_time
            today_iso = date.today().isoformat()
            tasks_today = tasks_mod.list_tasks_for_date(today_iso) or []
            summary = summarize_free_time(tasks_today, today_iso)
            return _as_reply("free_time_summary", summary)
        except Exception:
            return _as_reply("free_time_summary", "Nie mogę teraz policzyć wolnego czasu.")

    # =============================
    # PLAN DNIA
    # =============================
    if low in {"plan dnia", "co dziś", "co dzis", "dzisiaj", "dziś"}:
        try:
            from app.b2c.day_plan import build_day_plan
            today_iso = date.today().isoformat()
            tasks_today = tasks_mod.list_tasks_for_date(today_iso) or []
            origin_addr = _get_origin_address()
            transport_default = _get_place("travel_mode_default") or "samochodem"
            plan = build_day_plan(tasks_today, today_iso, origin_addr, transport_default, buffer_min=TRAVEL_BUFFER_MIN)
            return _as_reply("day_plan", plan)
        except Exception:
            return _as_reply("day_plan", "Nie mogę teraz wygenerować planu dnia.")


    # =============================
    # TRAVEL mode + ETA (MVP)
    # =============================
    if low.startswith("tryb:"):
        raw = message.split(":", 1)[1].strip()
        mode_norm = _normalize_travel_mode(raw)
        if not mode_norm:
            return _as_reply("set_travel_mode", "Podaj tryb: `samochód`, `autobus/komunikacja`, `rower`, `pieszo`.")
        _set_place("travel_mode_default", mode_norm)
        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}[mode_norm]
        return _as_reply("set_travel_mode", f"✅ Ustawiono tryb: {pretty}.")

    # Shortcuts without "tryb:"
    # If travel flow is active, do not swallow transport here.
    # Let the pending travel handler below calculate ETA / leave time.
    pending_t_guard = tasks_mod.get_pending_travel()
    mode_norm = _normalize_travel_mode(low)
    if (not pending_t_guard) and mode_norm and low in {"samochod","samochód","samochodem","autobus","komunikacja","komunikacją","rower","rowerem","pieszo"}:
        _set_place("travel_mode_default", mode_norm)
        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}[mode_norm]
        return _as_reply("set_travel_mode", f"✅ Ustawiono tryb: {pretty}.")



    if low in {"czy zdążę", "czy zdzaze", "spóźnię się?", "spoznie sie?", "spoznie sie", "spóźnię się", "czy sie spoznie", "czy się spóźnię"}:
        today = date.today()
        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(today) or [])
        # only tasks that have both time and location
        cand = []
        for t in tasks:
            if not isinstance(t, dict):
                continue
            due_at = str(t.get("due_at") or "")
            if "T" not in due_at:
                continue
            if not (t.get("location") or t.get("place")):
                continue
            cand.append(t)

        if not cand:
            return _as_reply("late_check", "Nie mam dziś zadania z godziną i adresem. Dodaj np. `dodaj: dentysta dziś 18:30 Narbutta 86, Warszawa`.")

        t = cand[0]
        destination = str(t.get("location") or t.get("place") or "").strip()
        origin = _get_origin_address()
        if not origin:
            return _as_reply("late_check", "Skąd ruszasz? Ustaw `ustaw dom: ...` albo `tu jestem: ...`.")

        travel_mode = str(t.get("travel_mode") or _get_place("travel_mode_default") or "samochod")
        mins = _mvp_eta_minutes(travel_mode)

        due_at = str(t.get("due_at") or "")
        try:
            dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone().replace(tzinfo=None)
        except Exception:
            return _as_reply("late_check", "Nie potrafię odczytać godziny tego zadania.")

        now = datetime.now()
        deadline = dt - timedelta(minutes=mins + TRAVEL_BUFFER_MIN)
        delta = deadline - now

        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}.get(_normalize_travel_mode(travel_mode) or "samochod", "samochód")
        leave_hhmm = deadline.strftime("%H:%M")

        # minutes as integers
        mins_left = int(math.ceil(delta.total_seconds() / 60.0))
        if delta.total_seconds() >= 0:
            return _as_reply(
                "late_check",
                f"✅ Zdążysz. Masz jeszcze **{mins_left} min**.\nWyjdź o **{leave_hhmm}** (bufor {TRAVEL_BUFFER_MIN} min).\nETA ({pretty}): {mins} min\n{origin} → {destination}",
            )

        late_by = int(math.ceil((now - deadline).total_seconds() / 60.0))
        return _as_reply(
            "late_check",
            f"⏰ Powinnaś wyjść **{late_by} min temu**.\nSpóźnisz się około **{late_by} min** (przy stałym ETA).\nWyjdź teraz.\nETA ({pretty}): {mins} min\n{origin} → {destination}",
        )


    if low.startswith("eta"):
        # eta or eta <nr>
        parts = (message or "").strip().split()
        want_no = None
        if len(parts) >= 2:
            try:
                want_no = int(parts[1])
            except Exception:
                want_no = None

        today = date.today()
        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(today) or [])
        # keep only tasks with a location
        tasks_loc = [t for t in tasks if isinstance(t, dict) and (t.get("location") or t.get("place"))]
        if not tasks_loc:
            return _as_reply("eta", "Nie mam dzisiaj zadania z adresem. Dodaj np. `dodaj: dentysta dziś 18:30 Narbutta 86, Warszawa`.")

        t = None
        if want_no is not None:
            idx = want_no - 1
            if 0 <= idx < len(tasks_loc):
                t = tasks_loc[idx]
        if t is None:
            t = tasks_loc[0]

        destination = str(t.get("location") or t.get("place") or "").strip()
        if not destination:
            return _as_reply("eta", "To zadanie nie ma adresu.")

        origin = _get_origin_address()
        if not origin:
            return _as_reply("eta", "Skąd ruszasz? Ustaw `ustaw dom: ...` albo `tu jestem: ...`.")

        travel_mode = str(t.get("travel_mode") or _get_place("travel_mode_default") or "samochod")
        mins = _mvp_eta_minutes(travel_mode)

        # Leave time if we have due_at with time
        due_at = str(t.get("due_at") or "")
        leave_line = ""
        if "T" in due_at:
            try:
                dt = datetime.fromisoformat(due_at.replace("Z","+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.astimezone().replace(tzinfo=None)
                leave_dt = dt - timedelta(minutes=mins + TRAVEL_BUFFER_MIN)
                leave_line = f"\nWyjdź o **{leave_dt.strftime('%H:%M')}** (bufor {TRAVEL_BUFFER_MIN} min)."
            except Exception:
                leave_line = ""

        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}.get(_normalize_travel_mode(travel_mode) or "samochod", "samochód")
        return _as_reply("eta", f"ETA ({pretty}): **{mins} min**\n{origin} → {destination}{leave_line}")
    if low.startswith("start:"):
        arg = message.split(":", 1)[1].strip().lower()
        if arg in {"dom", "home"}:
            ok = _set_origin_mode(ORIGIN_HOME)
            return _as_reply("set_origin_mode", "✅ Start ustawiony: dom." if ok else "Nie udało się ustawić.")
        if arg in {"praca", "work"}:
            ok = _set_origin_mode(ORIGIN_WORK)
            return _as_reply("set_origin_mode", "✅ Start ustawiony: praca." if ok else "Nie udało się ustawić.")
        if arg in {"tu", "obecna", "current"}:
            ok = _set_origin_mode(ORIGIN_CURRENT)
            return _as_reply("set_origin_mode", "✅ Start ustawiony: obecna lokalizacja (tu)." if ok else "Nie udało się ustawić.")
        return _as_reply("set_origin_mode", "Użyj: `start: dom` / `start: praca` / `start: tu`.")

    # =============================
    # SORT (toggle)
    # =============================
    if low.startswith("sort"):
        parts = low.split()
        if len(parts) == 1:
            cur = _get_sort_mode()
            label = "priorytet" if cur == SORT_PRIORITY else "czas"
            return _as_reply("sort_mode", f"Aktualne sortowanie: **{label}**. Ustaw: `sort priorytet` lub `sort czas`.")
        arg = parts[1]
        if arg in {"priorytet", "priority", "p"}:
            ok = _set_sort_mode(SORT_PRIORITY)
            return _as_reply("sort_mode", "✅ Ustawiono sortowanie: **priorytet**." if ok else "Nie udało się zapisać.")
        if arg in {"czas", "time", "t"}:
            ok = _set_sort_mode(SORT_TIME)
            return _as_reply("sort_mode", "✅ Ustawiono sortowanie: **czas**." if ok else "Nie udało się zapisać.")
        return _as_reply("sort_mode", "Użyj: `sort priorytet` albo `sort czas`.")

    # =============================
    # PRIORYTET (dla istniejącego zadania)
    # priorytet 2 p1
    # priorytet jutro 2 p3
    # priorytet 2026-02-22 2 p1
    # =============================
    if low.startswith("priorytet"):
        parts = low.split()
        if len(parts) not in {3, 4}:
            return _as_reply("set_priority", "Użyj: `priorytet 2 p1` albo `priorytet jutro 2 p3`.")

        if len(parts) == 3:
            target_date = date.today()
            n_s = parts[1]
            p_s = parts[2]
        else:
            target_date = _parse_date_arg(parts[1])
            if target_date is None:
                return _as_reply("set_priority", "Nie rozumiem daty. Użyj: `priorytet jutro 2 p3` albo `priorytet 2026-02-22 2 p1`.")
            n_s = parts[2]
            p_s = parts[3]

        try:
            n = int(n_s)
        except Exception:
            return _as_reply("set_priority", "Podaj numer z listy, np. `priorytet 2 p1`.")

        m = re.match(r"^p?(\d)$", p_s)
        if not m:
            return _as_reply("set_priority", "Podaj priorytet jako p1..p5, np. `priorytet 2 p1`.")
        pr = int(m.group(1))
        if pr < 1 or pr > 5:
            return _as_reply("set_priority", "Priorytet musi być w zakresie p1..p5.")

        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(target_date) or [])
        if not (1 <= n <= len(tasks)):
            return _as_reply("set_priority", f"Nie ma zadania #{n} na {_label_for_date(target_date)}.")

        tid = int(tasks[n - 1].get("id"))
        out = tasks_mod.update_task(tid, priority=pr, priority_explicit=True)
        if not out:
            return _as_reply("set_priority", "Nie udało się ustawić priorytetu.")

        emoji = PRIORITY_EMOJI.get(pr, f"p{pr}")
        return _as_reply("set_priority", f"✅ Ustawiono priorytet {emoji} dla zadania #{n} na {_label_for_date(target_date)}.")


    # =============================
    # DEV / RESET DZIŚ
    # =============================
    if low in {"/reset_dzis", "/reset dzis", "/reset dziś", "reset dzis", "reset dziś"}:
        removed = 0
        try:
            removed = int(tasks_mod.clear_tasks_for_date(date.today().isoformat()))
        except Exception:
            removed = 0
        for fn_name in ("clear_pending_travel", "clear_pending_reminder", "clear_pending_checklist", "clear_pending_clear"):
            try:
                fn = getattr(tasks_mod, fn_name, None)
                if fn:
                    fn()
            except Exception:
                pass
        return _as_reply("reset_today", f"🧹 Usunięto {removed} zadań na dziś.")

    # =============================
    # DELETE (LIVE numeracja) + data
    # usuń 2
    # usuń jutro 2
    # usuń 2026-02-22 2
    # =============================
    if low.startswith("usuń") or low.startswith("usun"):
        parts = low.split()
        parsed = _extract_date_and_index(parts, default_date=date.today())
        if not parsed:
            return _as_reply("delete_task", "Użyj: `usuń 2` albo `usuń jutro 2` albo `usuń 2026-02-22 2`.")

        target_date, n = parsed
        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(target_date) or [])

        if 1 <= n <= len(tasks):
            tid = int(tasks[n - 1].get("id"))
            tasks_mod.delete_task_by_id(tid)
            return _as_reply("delete_task", f"🗑 Usunięto zadanie #{n} na {_label_for_date(target_date)}.")

        # fallback: traktuj jako ID tylko dla formatu "usuń <liczba>"
        if len(parts) == 2:
            out = tasks_mod.delete_task_by_id(n)
            return _as_reply("delete_task", _reply_from_any(out, default=f"🗑 Usunięto zadanie #{n}."))
        return _as_reply("delete_task", f"Nie ma zadania #{n} na {_label_for_date(target_date)}.")

    # =============================
    # LISTA (LIVE numeracja) + data
    # lista / lista dziś / lista jutro / lista YYYY-MM-DD
    # + ETA tylko dla zadań z godziną
    # =============================
    if low.startswith("lista") or low == "list":
        parts = (low.split() if low != "list" else ["lista"])
        target_date = date.today()

        if len(parts) >= 2:
            d = _parse_date_arg(parts[1])
            if d is None:
                return _as_reply("list_tasks", "Nie rozumiem daty. Użyj: `lista jutro` albo `lista 2026-02-22`.")
            target_date = d

        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(target_date) or [])
        if not tasks:
            return _as_reply("list_tasks", f"Brak zaplanowanych zadań na {_label_for_date(target_date)}.")

        origin = _get_origin_address()
        api_key_present = bool(os.getenv("GOOGLE_MAPS_API_KEY"))

        lines = [f"**Najważniejsze na {_label_for_date(target_date)}:**"]
        for idx, t in enumerate(tasks, start=1):
            title = str(t.get("title") or "(bez tytułu)").strip()
            loc = str(t.get("location") or "").strip()
            time_s = _task_time_str(t)
            when = f"{time_s} — " if time_s else ""

            # Emoji priorytetu:
            # - p1: 🔴 zawsze
            # - p2: 🟠 tylko jeśli jawnie nadany (priority_explicit=True)
            # - p3: 🟢 zawsze
            emoji = ""
            try:
                pr = int(t.get("priority")) if t.get("priority") is not None else None
            except Exception:
                pr = None
            explicit = bool(t.get("priority_explicit"))
            if pr in PRIORITY_EMOJI:
                if pr == 2:
                    if explicit:
                        emoji = PRIORITY_EMOJI[pr] + " "
                else:
                    emoji = PRIORITY_EMOJI[pr] + " "
            elif pr:
                if pr == 2:
                    if explicit:
                        emoji = "p2 "
                else:
                    emoji = f"p{pr} "

            # ETA only if task has time
            eta_s = ""
            travel_mode = t.get("travel_mode") or t.get("mode")
            gm = _google_mode_from_task(str(travel_mode or ""))
            if api_key_present and origin and loc and time_s and gm:
                minutes = get_eta_minutes(origin=origin, destination=loc, mode=gm)
                if minutes is not None:
                    eta_s = f" (ETA: {minutes} min)"

            tail = f", {loc}" if loc else ""
            lines.append(f"• #{idx} {emoji}{when}{title}{tail}{eta_s}")

        # Small hint if not configured
        if not api_key_present:
            lines.append("")
            lines.append("_Aby włączyć ETA: ustaw zmienną środowiskową `GOOGLE_MAPS_API_KEY`._")
        elif not origin:
            lines.append("")
            lines.append("_Aby włączyć ETA: ustaw `ustaw dom:` lub `ustaw praca:` albo `tu jestem:`._")

        return _as_reply("list_tasks", "\n".join(lines))

    # =============================
    # Pending reminder FIRST
    # =============================
    pending_r = tasks_mod.get_pending_reminder()
    if pending_r:
        task_id = int(pending_r.get("task_id"))
        reminder_at = str(pending_r.get("reminder_at"))
    
        if low in YES:
            tasks_mod.clear_pending_reminder()
            out = tasks_mod.set_reminder(task_id, reminder_at, enabled=True)
    
            # Make numbering consistent with the live list (router numbering), not internal task IDs.
            live_no = None
            try:
                t = tasks_mod.get_task(task_id)
                if t:
                    due_at = str(t.get("due_at") or "")
                    due_date = due_at.split("T", 1)[0] if "T" in due_at else (due_at[:10] if len(due_at) >= 10 else "")
                    tasks_for_day: List[Dict[str, Any]] = []
                    if due_date:
                        if hasattr(tasks_mod, "list_tasks_for_date"):
                            tasks_for_day = tasks_mod.list_tasks_for_date(due_date) or []
                        elif hasattr(tasks_mod, "list_tasks"):
                            tasks_for_day = tasks_mod.list_tasks(date=due_date) or []
                    tasks_for_day = _sort_for_list(tasks_for_day)
                    for i, tt in enumerate(tasks_for_day, start=1):
                        if tt.get("id") == task_id:
                            live_no = i
                            break
            except Exception:
                live_no = None
    
            if isinstance(out, dict):
                if live_no is not None:
                    out["reply"] = f"⏰ Ustawiłem przypomnienie dla zadania #{live_no} na **{reminder_at}**."
                else:
                    out["reply"] = f"⏰ Ustawiłem przypomnienie na **{reminder_at}**."
            return _as_reply("set_reminder", _reply_from_any(out, default=f"⏰ Ustawiono przypomnienie na {reminder_at}."))
    
        if low in NO:
            tasks_mod.clear_pending_reminder()
            return _as_reply("set_reminder", "OK — bez przypomnienia.")
    
        if not _is_command_like(message):
            return _as_reply("set_reminder", f"Ustawić przypomnienie na **{reminder_at}**? (tak/nie)")
    
    # ============================
    # Pending clear-day confirmation
    # ============================
    pending_clear = tasks_mod.get_pending_clear()
    if pending_clear:
        ans = low.strip()
        if ans in ("tak", "t", "yes", "y"):
            date_iso = str(pending_clear.get("date") or "")
            removed = tasks_mod.clear_tasks_for_date(date_iso)
            tasks_mod.clear_pending_clear()
            return _as_reply("cleared_day", f"🧹 Usunięto {removed} zadań na {date_iso}.")
        if ans in ("nie", "n", "no"):
            tasks_mod.clear_pending_clear()
            return _as_reply("clear_cancelled", "OK, nie usuwam.")
        return _as_reply("confirm_clear_day", "Na pewno usunąć **wszystkie** zadania na dziś? (tak/nie)")
    # Pending travel (2-step: start -> mode)
    # =============================
    pending_t = tasks_mod.get_pending_travel()
    if pending_t:
        created_from = str(pending_t.get("created_from") or "")
        skip_pending_for_new_command = _looks_like_new_task_request(message)
        try:
            pending_task_id = int(pending_t.get("task_id"))
        except Exception:
            pending_task_id = None
    
        # Step 1: ask/handle START (always after adding timed+location task)
        if created_from == "add_start" and pending_task_id is not None and not skip_pending_for_new_command:
            if _is_command_like(message) or not (message or '').strip():
                return _as_reply("set_origin_mode", "Skąd ruszasz? Napisz: `dom` / `praca` / `tu` albo podaj adres startu.")
    
            ans = (message or "").strip()
            mode_key, origin_addr = _resolve_origin_from_answer(ans)
            if mode_key == ORIGIN_HOME:
                _set_place("origin_mode", ORIGIN_HOME)
            elif mode_key == ORIGIN_WORK:
                _set_place("origin_mode", ORIGIN_WORK)
            elif mode_key == ORIGIN_CURRENT:
                _set_place("origin_mode", ORIGIN_CURRENT)
            else:
                _set_place("origin_custom", ans)
                _set_place("origin_mode", ORIGIN_CUSTOM)

            try:
                tasks_mod.update_task(
                    pending_task_id,
                    start_origin_mode=mode_key,
                    start_origin=origin_addr or ans,
                )
            except Exception:
                pass
    
            # If task already has travel mode, skip asking and go straight to reminder proposal
            t = tasks_mod.get_task(pending_task_id)
            travel_mode = (t or {}).get("travel_mode") or (t or {}).get("mode")
            if travel_mode:
                tasks_mod.clear_pending_travel()
    
                origin = _get_origin_address()
                loc = (t or {}).get("location")
                due_at = (t or {}).get("due_at")
                gm = _google_mode_from_task(str(travel_mode))
                if origin and loc and due_at and gm and os.getenv("GOOGLE_MAPS_API_KEY"):
                    mins = get_eta_minutes(origin=origin, destination=str(loc), mode=gm)
                    if mins is not None:
                        try:
                            dt = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
                        except Exception:
                            dt = None
                        if dt is not None:
                            if dt.tzinfo is not None:
                                dt = dt.astimezone().replace(tzinfo=None)
                            remind_dt = dt - timedelta(minutes=int(mins) + 10)
                            reminder_at = remind_dt.strftime("%Y-%m-%dT%H:%M")
                            try:
                                tasks_mod.update_task(
                                    pending_task_id,
                                    eta_min=int(mins),
                                    leave_at=remind_dt.strftime("%H:%M"),
                                    reminder_at=reminder_at,
                                    start_origin=origin,
                                )
                            except Exception:
                                pass
                            tasks_mod.set_pending_reminder(pending_task_id, reminder_at, created_from="add")
                            return _as_reply("set_reminder", f"✅ OK. Start: **{origin}**. ETA: **{mins} min**. Proponuję wyjść o **{remind_dt.strftime('%H:%M')}**. Ustawić przypomnienie? (tak/nie)")
    
                return _as_reply("set_origin_mode", "✅ OK.")
    
            # Next: ask for travel mode
            tasks_mod.set_pending_travel(pending_task_id, created_from="add_mode")
            return _as_reply("set_travel_mode", "✅ OK. Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
    
        # Step 2: handle travel mode
        if created_from == "add_mode" and pending_task_id is not None and not skip_pending_for_new_command:
            if _is_command_like(message) or not (message or "").strip():
                return _as_reply("set_travel_mode", "✅ OK. Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
            out = tasks_mod.apply_travel_mode_to_pending(message)
            if out is None:
                return _as_reply("set_travel_mode", "Nie złapałam sposobu dojazdu. Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
            if out is not None:
                t = tasks_mod.get_task(pending_task_id)
                origin = _get_origin_address()
                loc = (t or {}).get("location")
                due_at = (t or {}).get("due_at")
                travel_mode = (t or {}).get("travel_mode") or (t or {}).get("mode")
                gm = _google_mode_from_task(str(travel_mode or ""))
                if origin and loc and due_at and gm and os.getenv("GOOGLE_MAPS_API_KEY"):
                    mins = get_eta_minutes(origin=origin, destination=str(loc), mode=gm)
                    if mins is not None:
                        try:
                            dt = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
                        except Exception:
                            dt = None
                        if dt is not None:
                            if dt.tzinfo is not None:
                                dt = dt.astimezone().replace(tzinfo=None)
                            remind_dt = dt - timedelta(minutes=int(mins) + 10)
                            reminder_at = remind_dt.strftime("%Y-%m-%dT%H:%M")
                            try:
                                tasks_mod.update_task(
                                    pending_task_id,
                                    eta_min=int(mins),
                                    leave_at=remind_dt.strftime("%H:%M"),
                                    reminder_at=reminder_at,
                                    start_origin=origin,
                                )
                            except Exception:
                                pass
                            tasks_mod.set_pending_reminder(pending_task_id, reminder_at, created_from="add")
                            base = _reply_from_any(out, default="OK")
                            return _as_reply("set_reminder", f"{base}\n\nStart: **{origin}**. ETA: **{mins} min**. Proponuję wyjść o **{remind_dt.strftime('%H:%M')}**. Ustawić przypomnienie? (tak/nie)")
    
                return _as_reply("set_travel_mode", _reply_from_any(out, default="OK"))
    
            if not _is_command_like(message):
                return _as_reply("set_travel_mode", "Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
    
        # fallback (older flows)
        if not skip_pending_for_new_command:
            out = tasks_mod.apply_travel_mode_to_pending(message)
            if out is not None:
                return _as_reply("set_travel_mode", _reply_from_any(out, default="OK"))
            if not _is_command_like(message):
                return _as_reply("set_travel_mode", "Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")


    # ===== INBOX v4 TASK CONVERSION =====
    m_create_task = re.match(r"^utw[oó]rz zadanie z inbox\s+(\d+)\s+(.+)$", message, flags=re.I)
    if m_create_task:
        from app.b2c import inbox as inbox_mod
        n = int(m_create_task.group(1))
        suffix = m_create_task.group(2).strip()
        item = inbox_mod.get_inbox_by_live_number(n)
        if not item:
            return _as_reply("inbox_to_task", f"Nie ma wpisu #{n} w Inbox.")
        kind = str(item.get("kind") or "").strip().lower()
        if kind and kind != "task":
            return _as_reply("inbox_to_task", f"Wpis #{n} ma typ `{kind}`. Dla tasków użyj wpisu typu `[task]`.")
        synthetic = f"dodaj: {item['text']} {suffix}".strip()
        out = tasks_mod.add_task(synthetic)
        task = out.get("task") if isinstance(out, dict) else None
        if isinstance(task, dict):
            inbox_mod.pop_inbox_by_live_number(n)
        return _as_reply("inbox_to_task", _reply_from_any(out, default="OK"))

    # ===== INBOX v3 PROCESSING =====
    if low == "przetwórz inbox" or low == "przetworz inbox":
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.preview_processing()
        return _as_reply("inbox_process_preview", out.get("reply", "Inbox jest pusty."))

    if low.startswith("przetwórz inbox ") or low.startswith("przetworz inbox "):
        from app.b2c import inbox as inbox_mod
        m = re.search(r"(\d+)$", low)
        if not m:
            return _as_reply("inbox_process", "Użyj: `przetwórz inbox 1`.")
        out = inbox_mod.process_inbox_item(int(m.group(1)))
        return _as_reply("inbox_process", out.get("reply", "OK"))

    if low == "pomysły" or low == "pomysly":
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.list_bucket(inbox_mod.IDEAS_FILE, "Pomysły")
        return _as_reply("ideas_list", out.get("reply", "Pomysły są puste."))

    if low == "notatki":
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.list_bucket(inbox_mod.NOTES_FILE, "Notatki")
        return _as_reply("notes_list", out.get("reply", "Notatki są puste."))

    if low == "reminders":
        from app.b2c import inbox as inbox_mod
        out = inbox_mod.list_bucket(inbox_mod.REMINDERS_FILE, "Reminders")
        return _as_reply("reminders_list", out.get("reply", "Reminders są puste."))

    # CHECKLISTA przypięta do zadania
    # =============================
    def _resolve_task_for_live_number(num: int, d: date | None = None) -> Optional[Dict[str, Any]]:
        d = d or date.today()
        tasks_for_day = _sort_for_list(tasks_mod.list_tasks_for_date(d) or [])
        if 1 <= num <= len(tasks_for_day):
            return tasks_for_day[num - 1]
        return None

    m_add_checklist = re.match(r"^dodaj do zadania\s+(\d+)\s+([^:]+):\s*(.+)$", message, flags=re.I)
    if m_add_checklist:
        live_no = int(m_add_checklist.group(1))
        list_title = m_add_checklist.group(2).strip().rstrip(":")
        items_raw = m_add_checklist.group(3).strip()
        task_live = _resolve_task_for_live_number(live_no)
        if not task_live:
            return _as_reply("checklist", f"Nie ma zadania #{live_no} na dziś.")

        items = [x.strip().lstrip("-").strip() for x in items_raw.split(",") if x.strip().lstrip("-").strip()]
        if not items:
            return _as_reply("checklist", "Podaj pozycje listy po dwukropku, np. `dodaj do zadania 1 kup: mleko, chleb`.")

        checklist = {
            "title": list_title or "Lista",
            "items": [{"text": item, "done": False} for item in items],
        }
        saved = tasks_mod.update_task(int(task_live.get("id")), checklist=checklist) if hasattr(tasks_mod, "update_task") else None
        if not saved:
            return _as_reply("checklist", "Nie udało się dodać checklisty.")

        lines = [f"✅ Dodano checklistę do zadania #{live_no}", "", f"{checklist['title']}:"]
        for idx_i, item in enumerate(checklist["items"], start=1):
            lines.append(f"{live_no}.{idx_i} ☐ {item['text']}")
        return _as_reply("checklist", "\n".join(lines))

    m_add_to = re.match(r"^dodaj do\s+(\d+)\s*:\s*(.+)$", message, flags=re.I)
    if m_add_to:
        live_no = int(m_add_to.group(1))
        item_text = m_add_to.group(2).strip()
        task_live = _resolve_task_for_live_number(live_no)
        if not task_live:
            return _as_reply("checklist", f"Nie ma zadania #{live_no} na dziś.")
        ok = tasks_mod.add_checklist_item_manual(int(task_live.get("id")), item_text) if hasattr(tasks_mod, "add_checklist_item_manual") else None
        return _as_reply("checklist", f"✅ Dodano: {item_text}" if ok else "Nie udało się dodać pozycji.")

    # NLP TASK INPUT (v9)
    synthetic_add = _build_nlp_add_command(message)
    if synthetic_add:
        message = synthetic_add
        low = message.strip().lower()

    # =============================
    # STABLE NLP (czas względny / naturalny / checklist task)
    # =============================
    nlp_out = _maybe_handle_stable_nlp(message)
    if nlp_out is not None:
        return nlp_out

    # DODAJ (spójny numer LIVE z listą)
    # =============================
    if low.startswith("dodaj:") or low.startswith("dodaj "):
        out = tasks_mod.add_task(message)
    
        # spróbuj wyciągnąć task_id i datę zadania z odpowiedzi tasks_mod
        task = out.get("task") if isinstance(out, dict) else None
        tid = None
        task_date = date.today()
    
        if isinstance(task, dict):
            try:
                tid = int(task.get("id")) if task.get("id") is not None else None
            except Exception:
                tid = None
    
            due_at = task.get("due_at")
            due_date = task.get("due_date")
    
            # Canonical: if we have due_at (date+time), use that date.
            if isinstance(due_at, str) and len(due_at) >= 10:
                try:
                    task_date = date.fromisoformat(due_at[:10])
                except Exception:
                    task_date = date.today()
            elif isinstance(due_date, str):
                try:
                    task_date = date.fromisoformat(due_date)
                except Exception:
                    task_date = date.today()
    
        # fallback: parsuj ID z tekstu odpowiedzi
        if tid is None:
            txt = _reply_from_any(out, default="")
            m = re.search(r"#(\d+)", txt)
            if m:
                try:
                    tid = int(m.group(1))
                except Exception:
                    tid = None
    
        if tid is not None:
            tasks_for_day = _sort_for_list(tasks_mod.list_tasks_for_date(task_date) or [])
    
            matched: Optional[Tuple[int, Dict[str, Any]]] = None
    
            # 1) Prefer match by internal stable id
            if tid is not None:
                for idx, t in enumerate(tasks_for_day, start=1):
                    try:
                        if str(t.get("id")) == str(tid):
                            matched = (idx, t)
                            break
                    except Exception:
                        continue
    
            # 2) Fallback: match by (due_at + title) from returned task payload
            if matched is None and isinstance(task, dict):
                want_title = str(task.get("title") or "").strip()
                want_due_at = str(task.get("due_at") or "").strip()
                if want_title or want_due_at:
                    for idx, t in enumerate(tasks_for_day, start=1):
                        try:
                            if want_due_at and str(t.get("due_at") or "").strip() != want_due_at:
                                continue
                            if want_title and str(t.get("title") or "").strip() != want_title:
                                continue
                            matched = (idx, t)
                            break
                        except Exception:
                            continue
    
            if matched is not None:
                idx, t = matched
                title = str(t.get("title") or "(bez tytułu)").strip()
                base_msg = f"✅ Dodane zadanie #{idx}: {title} (na {_label_for_date(task_date)})"
    
                # If task has a concrete hour AND location, start a short flow: ALWAYS ask START, then travel mode.
                has_time = bool(_task_time_str(t))
                has_loc = bool(t.get("location"))
                if has_time and has_loc:
                    # keep stable id (not live number) in pending flow
                    try:
                        tasks_mod.set_pending_travel(int(t.get("id")), created_from="add_start")
                    except Exception:
                        if tid is not None:
                            tasks_mod.set_pending_travel(int(tid), created_from="add_start")
                    return _as_reply(
                        "set_origin_mode",
                        base_msg + "\n\nSkąd ruszasz? Napisz: `dom` / `praca` / `tu` albo podaj adres startu."
                    )
    
                return _as_reply("add_task", base_msg)
    
        return _as_reply("add_task", _reply_from_any(out))
    
    # =============================
    # =============================
    # MORNING (no questions; just overview + refresh ETA cache)
    # =============================
    if low in {"rano", "dzień dobry", "dzien dobry", "poranek"}:
        today = date.today()
        tasks_today = _sort_for_list(tasks_mod.list_tasks_for_date(today) or [])
        if not tasks_today:
            return _as_reply("morning", "Dzień dobry 🙂 Dziś nie masz żadnych zadań na liście.")
    
        c1 = c2 = c3 = 0
        for t in tasks_today:
            pr = t.get("priority")
            if pr == 1:
                c1 += 1
            elif pr == 2:
                c2 += 1
            elif pr == 3:
                c3 += 1
    
        api_key_present = bool(os.getenv("GOOGLE_MAPS_API_KEY"))
        origin = _get_origin_address()
    
        out_lines = []
        out_lines.append(f"Dzień dobry 🙂 Masz dziś **{len(tasks_today)}** zadań. (p1: {c1}, p2: {c2}, p3: {c3})")
        out_lines.append("")
        out_lines.append("**Najbliższe z godziną:**")
    
        shown = 0
        for t in tasks_today:
            time_s = _task_time_str(t)
            if not time_s:
                continue
            title = str(t.get("title") or "(bez tytułu)").strip()
            loc = t.get("location")
            pr = t.get("priority")
            emoji = _priority_emoji(pr, bool(t.get("priority_explicit")))
    
            eta_s = ""
            travel_mode = t.get("travel_mode") or t.get("mode")
            gm = _google_mode_from_task(str(travel_mode or ""))
            if api_key_present and origin and loc and gm:
                mins = get_eta_minutes(origin=origin, destination=str(loc), mode=gm)
                if mins is not None:
                    eta_s = f" (ETA: {mins} min)"
    
            tail = f", {loc}" if loc else ""
            out_lines.append(f"• {emoji}{time_s} — {title}{tail}{eta_s}")
            shown += 1
            if shown >= 3:
                break
    
        if shown == 0:
            out_lines.append("• (brak zadań z konkretną godziną)")
    
        return _as_reply("morning", "\n".join(out_lines))
    return _as_reply("unknown", "Nie mam jeszcze tej komendy. Spróbuj: `lista`, `dodaj: ...`, `usuń ...`, `priorytet ...`.")