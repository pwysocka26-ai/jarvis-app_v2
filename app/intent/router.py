from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple
import re
from datetime import date, datetime, timedelta

from app.b2c import tasks as tasks_mod
from app.b2c.travel_mode import morning_brief

YES = {"tak", "t", "yes", "y", "ok", "jasne", "pewnie"}
NO = {"nie", "n", "no"}


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


def _parse_time_to_minutes(t: Optional[str]) -> Optional[int]:
    if not t:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", str(t).strip())
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
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
    """Order for display & delete-by-position.

    - Tasks with a time first (chronological).
    - Tasks without time after timed tasks, ordered by created_at.
    """

    def key(t: Dict[str, Any]):
        time_min = _parse_time_to_minutes(t.get("time"))
        has_time = 0 if time_min is not None else 1
        created = _parse_created_at(t.get("created_at")) or datetime.max
        time_key = time_min if time_min is not None else 10**9
        return (has_time, time_key, created)

    return sorted([t for t in tasks if isinstance(t, dict)], key=key)


def _label_for_date(d: date) -> str:
    if d == date.today():
        return "dziś"
    if d == date.today() + timedelta(days=1):
        return "jutro"
    return d.isoformat()


def _parse_date_token(tok: str) -> Optional[date]:
    t = (tok or "").strip().lower()
    if t in {"dziś", "dzis", "dzisiaj"}:
        return date.today()
    if t == "jutro":
        return date.today() + timedelta(days=1)
    try:
        return date.fromisoformat(tok)
    except Exception:
        return None


def _pick_date_and_index(parts: List[str], default_date: date) -> Tuple[Optional[date], Optional[int]]:
    """Parse commands like:
    - ['usuń','2'] -> (default_date, 2)
    - ['usuń','jutro','2'] -> (tomorrow, 2)
    - ['usuń','2026-02-22','2'] -> (iso_date, 2)
    """
    if len(parts) < 2:
        return None, None

    if len(parts) == 2:
        # usuń 2
        try:
            return default_date, int(parts[1])
        except Exception:
            return default_date, None

    # len >= 3: maybe date token + number
    d = _parse_date_token(parts[1])
    if d is None:
        # if second token isn't a date token, treat it as number and ignore rest
        try:
            return default_date, int(parts[1])
        except Exception:
            return default_date, None

    try:
        return d, int(parts[2])
    except Exception:
        return d, None


def route_intent(message: str, persona: str = "b2c", mode: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    low = (message or "").strip().lower()

    def _is_command_like(txt: str) -> bool:
        t = (txt or "").strip().lower()
        return (
            t.startswith("/")
            or t.startswith("lista")
            or t.startswith("dodaj")
            or t.startswith("usun")
            or t.startswith("usuń")
            or t.startswith("priorytet")
            or t.startswith("rano")
            or t.startswith("diag")
            or t.startswith("help")
        )

    # =============================
    # DELETE (LIVE numeracja) + data
    # =============================
    if low.startswith("usuń") or low.startswith("usun"):
        parts = low.split()
        target_date, n = _pick_date_and_index(parts, default_date=date.today())
        if n is None:
            return _as_reply("delete_task", "Użyj: `usuń 2` albo `usuń jutro 2` albo `usuń 2026-02-22 2`.")

        if target_date is None:
            target_date = date.today()

        tasks_raw = tasks_mod.list_tasks_for_date(target_date) or []
        tasks = _sort_for_list(tasks_raw)

        # delete by position
        if 1 <= n <= len(tasks):
            tid = int(tasks[n - 1].get("id"))
            tasks_mod.delete_task_by_id(tid)
            return _as_reply("delete_task", f"🗑 Usunięto zadanie #{n} ({_label_for_date(target_date)}).")

        # fallback: treat as ID (historical behavior)
        out = tasks_mod.delete_task_by_id(n)
        return _as_reply("delete_task", _reply_from_any(out, default=f"🗑 Usunięto zadanie #{n}."))

    # =============================
    # PRIORITY (update existing task)
    # =============================
    # Examples:
    # - priorytet 2 p1
    # - priorytet jutro 2 p3
    # - priorytet 2026-02-22 2 p1
    if low.startswith("priorytet"):
        parts = low.split()
        # expect: priorytet [date] <n> p<1-5>
        if len(parts) < 3:
            return _as_reply("set_priority", "Użyj: `priorytet 2 p1` albo `priorytet jutro 2 p3`.")

        # Determine if parts[1] is date token
        d = _parse_date_token(parts[1])
        if d is None:
            # priorytet 2 p1
            target_date = date.today()
            idx_pos = 1
        else:
            target_date = d
            idx_pos = 2

        if len(parts) <= idx_pos + 1:
            return _as_reply("set_priority", "Użyj: `priorytet 2 p1` albo `priorytet jutro 2 p3`.")

        try:
            n = int(parts[idx_pos])
        except Exception:
            return _as_reply("set_priority", "Podaj numer zadania, np: `priorytet 2 p1`.")

        p_token = parts[idx_pos + 1]
        m = re.match(r"^p([1-5])$", p_token)
        if not m:
            return _as_reply("set_priority", "Podaj priorytet jako `p1`..`p5`, np: `priorytet 2 p1`.")
        pr = int(m.group(1))

        tasks_raw = tasks_mod.list_tasks_for_date(target_date) or []
        tasks = _sort_for_list(tasks_raw)

        if not (1 <= n <= len(tasks)):
            return _as_reply("set_priority", f"Nie ma zadania #{n} na {_label_for_date(target_date)}.")

        tid = int(tasks[n - 1].get("id"))
        updated = tasks_mod.update_task(tid, priority=pr)

        if not updated:
            return _as_reply("set_priority", "Nie udało się ustawić priorytetu (zadanie nie znalezione).")

        return _as_reply("set_priority", f"✅ Ustawiono priorytet p{pr} dla zadania #{n} ({_label_for_date(target_date)}).")

    # =============================
    # LISTA (LIVE numeracja) + data
    # =============================
    if low.startswith("lista") or low == "list":
        parts = (low.split() if low != "list" else ["lista"])
        target_date = date.today()

        if len(parts) >= 2:
            d = _parse_date_token(parts[1])
            if d is None:
                return _as_reply("list_tasks", "Nie rozumiem daty. Użyj: `lista jutro` albo `lista 2026-02-22`.")
            target_date = d

        tasks_raw = tasks_mod.list_tasks_for_date(target_date) or []
        tasks = _sort_for_list(tasks_raw)

        if not tasks:
            return _as_reply("list_tasks", f"Brak zaplanowanych zadań na {_label_for_date(target_date)}.")

        lines = [f"**Najważniejsze na {_label_for_date(target_date)}:**"]
        pos = 0

        for t in tasks:
            pos += 1
            title = str(t.get("title") or "(bez tytułu)").strip()
            loc = str(t.get("location") or "").strip()
            time_s = str(t.get("time") or "").strip()
            when = f"{time_s} — " if time_s else ""

            meta = []

            # Priority: hide default p2 to reduce noise
            try:
                pr = int(t.get("priority")) if t.get("priority") is not None else None
            except Exception:
                pr = None
            if pr and pr != 2:
                meta.append(f"p{pr}")

            dur = t.get("duration_min") or t.get("duration")
            try:
                dur_i = int(dur) if dur is not None else None
            except Exception:
                dur_i = None

            if dur_i:
                if dur_i % 60 == 0 and dur_i >= 60:
                    meta.append(f"{dur_i//60}h")
                elif dur_i > 60:
                    meta.append(f"{dur_i//60}h{dur_i%60}m")
                else:
                    meta.append(f"{dur_i}m")

            meta_s = f" ({', '.join(meta)})" if meta else ""
            tail = f", {loc}" if loc else ""

            lines.append(f"• #{pos} {when}{title}{meta_s}{tail}")

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
            return _as_reply("set_reminder", _reply_from_any(out, default=f"⏰ Ustawiono przypomnienie na {reminder_at}."))

        if low in NO:
            tasks_mod.clear_pending_reminder()
            return _as_reply("set_reminder", "OK — bez przypomnienia.")

        if not _is_command_like(message):
            return _as_reply("set_reminder", f"Ustawić przypomnienie na **{reminder_at}**? (tak/nie)")

    # =============================
    # Pending travel
    # =============================
    pending_t = tasks_mod.get_pending_travel()
    if pending_t:
        out = tasks_mod.apply_travel_mode_to_pending(message)
        if out is not None:
            return _as_reply("set_travel_mode", _reply_from_any(out, default="OK"))

        if not _is_command_like(message):
            return _as_reply("set_travel_mode", "Jak jedziesz? Napisz: 'samochodem' / 'komunikacją' / 'rowerem' / 'pieszo'.")

    # =============================
    # DODAJ
    # =============================
    if low.startswith("dodaj:") or low.startswith("dodaj "):
        out = tasks_mod.add_task(message)
        return _as_reply("add_task", _reply_from_any(out))

    # =============================
    # MORNING
    # =============================
    if low in {"rano", "dzień dobry", "dzien dobry", "poranek"}:
        out = morning_brief()
        if isinstance(out, dict) and ("reply" in out or "response" in out):
            text = out.get("response") or out.get("reply")
            return {
                "intent": out.get("intent", "morning_brief"),
                "reply": text,
                "response": text,
                **{k: v for k, v in out.items() if k not in {"reply", "response"}},
            }
        return _as_reply("morning_brief", str(out))

    return _as_reply("unknown", "Nie mam jeszcze tej komendy. Spróbuj: 'rano' albo 'dodaj: ...'")
