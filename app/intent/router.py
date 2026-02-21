from __future__ import annotations

from typing import Any, Dict, Optional, List
import re
from datetime import date, datetime, timedelta

from app.b2c import tasks as tasks_mod
from app.b2c.travel_mode import morning_brief

YES = {"tak", "t", "yes", "y", "ok", "jasne", "pewnie"}
NO = {"nie", "n", "no"}

# Wersja A: emoji (działa wszędzie)
PRIORITY_EMOJI = {
    1: "🔴",  # p1 czerwone kółko
    2: "🟠",  # p2 pomarańczowe kółko (domyślne p2 ukrywamy w widoku)
    3: "🟢",  # p3 zielone kółko
}


SORT_PRIORITY = "priority"
SORT_TIME = "time"

def _get_sort_mode() -> str:
    """Persisted sort mode stored in tasks DB under settings.sort_mode."""
    try:
        db = tasks_mod.load_tasks_db()
        settings = db.get("settings", {}) if isinstance(db, dict) else {}
        mode = settings.get("sort_mode")
        if mode in {SORT_PRIORITY, SORT_TIME}:
            return mode
    except Exception:
        pass
    return SORT_PRIORITY

def _set_sort_mode(mode: str) -> bool:
    try:
        db = tasks_mod.load_tasks_db()
        if not isinstance(db, dict):
            return False
        settings = db.get("settings")
        if not isinstance(settings, dict):
            settings = {}
            db["settings"] = settings
        settings["sort_mode"] = mode
        tasks_mod.save_tasks_db(db)
        return True
    except Exception:
        return False


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
    """Sortowanie używane w `lista`, `usuń` oraz numeracji LIVE przy `dodaj`.

    Tryby:
    - priority (domyślnie): p1 najwyżej -> p2 -> p3..., potem czas
    - time: tylko czas (zadania z godziną najpierw, potem bez godziny po created_at)
    """
    mode = _get_sort_mode()

    def key(t: Dict[str, Any]):
        time_min = _parse_time_to_minutes(t.get("time"))
        has_time = 0 if time_min is not None else 1
        created = _parse_created_at(t.get("created_at")) or datetime.max
        time_key = time_min if time_min is not None else 10**9

        if mode == SORT_TIME:
            return (has_time, time_key, created)

        # SORT_PRIORITY (default): priority first
        try:
            pr = int(t.get("priority")) if t.get("priority") is not None else 2
        except Exception:
            pr = 2
        return (pr, has_time, time_key, created)

    return sorted([t for t in tasks if isinstance(t, dict)], key=key)


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


def _extract_date_and_index(parts: List[str], default_date: date) -> Optional[tuple[date, int]]:
    """Parse:
    - ['usuń','2'] -> (today,2)
    - ['usuń','jutro','2'] -> (tomorrow,2)
    - ['usuń','2026-02-22','2'] -> (date,2)
    """
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
    # SORT (przełączanie kolejności)
    # sort priorytet | sort czas | sort
    # =============================
    if low.startswith("sort"):
        parts = low.split()
        if len(parts) == 1:
            mode = _get_sort_mode()
            label = "priorytet" if mode == SORT_PRIORITY else "czas"
            return _as_reply("sort_mode", f"Aktualne sortowanie: **{label}**. Ustaw: `sort priorytet` lub `sort czas`.")
        if len(parts) >= 2:
            arg = parts[1]
            if arg in {"priorytet", "priority", "p"}:
                ok = _set_sort_mode(SORT_PRIORITY)
                return _as_reply("sort_mode", "✅ Ustawiono sortowanie: **priorytet**." if ok else "Nie udało się zapisać ustawienia sortowania.")
            if arg in {"czas", "time", "t"}:
                ok = _set_sort_mode(SORT_TIME)
                return _as_reply("sort_mode", "✅ Ustawiono sortowanie: **czas**." if ok else "Nie udało się zapisać ustawienia sortowania.")
        return _as_reply("sort_mode", "Użyj: `sort priorytet` albo `sort czas`.")

# =============================
    # PRIORYTET (dla istniejącego zadania)
    # priorytet 2 p1
    # priorytet jutro 2 p3
    # priorytet 2026-02-22 2 p1
    # =============================
    if low.startswith("priorytet"):
        parts = low.split()
        # Formaty:
        # priorytet <n> p<k>
        # priorytet <date> <n> p<k>
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

        task = tasks[n - 1]
        tid = int(task.get("id"))
        out = tasks_mod.update_task(tid, priority=pr, priority_explicit=True)
        if not out:
            return _as_reply("set_priority", "Nie udało się ustawić priorytetu.")

        # Informacyjnie: pokaż emoji (z ukrywaniem default p2 w liście, ale tu możemy potwierdzić p2 też)
        emoji = PRIORITY_EMOJI.get(pr, f"p{pr}")
        return _as_reply("set_priority", f"✅ Ustawiono priorytet {emoji} dla zadania #{n} na {_label_for_date(target_date)}.")

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

        # fallback: traktuj jako ID (stare zachowanie) tylko dla formatu "usuń <liczba>"
        if len(parts) == 2:
            out = tasks_mod.delete_task_by_id(n)
            return _as_reply("delete_task", _reply_from_any(out, default=f"🗑 Usunięto zadanie #{n}."))
        return _as_reply("delete_task", f"Nie ma zadania #{n} na {_label_for_date(target_date)}.")

    # =============================
    # LISTA (LIVE numeracja) + data
    # lista / lista dziś / lista jutro / lista YYYY-MM-DD
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

        lines = [f"**Najważniejsze na {_label_for_date(target_date)}:**"]
        for idx, t in enumerate(tasks, start=1):
            title = str(t.get("title") or "(bez tytułu)").strip()
            loc = str(t.get("location") or "").strip()
            time_s = str(t.get("time") or "").strip()
            when = f"{time_s} — " if time_s else ""

            # Emoji priorytetu:
            # - p1: 🔴 zawsze
            # - p2: 🟠 TYLKO jeśli zostało jawnie nadane (priority_explicit=True)
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

            tail = f", {loc}" if loc else ""
            lines.append(f"• #{idx} {emoji}{when}{title}{tail}")

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
    # DODAJ (spójny numer LIVE z listą)
    # =============================
    if low.startswith("dodaj:") or low.startswith("dodaj "):
        out = tasks_mod.add_task(message)

        # Spróbuj wyciągnąć task_id i datę zadania z odpowiedzi tasks_mod
        task = out.get("task") if isinstance(out, dict) else None
        tid = None
        task_date = date.today()

        if isinstance(task, dict):
            try:
                tid = int(task.get("id")) if task.get("id") is not None else None
            except Exception:
                tid = None

            # prefer due_date, else take date part of due_at
            due_date = task.get("due_date")
            due_at = task.get("due_at")
            if isinstance(due_date, str):
                try:
                    task_date = date.fromisoformat(due_date)
                except Exception:
                    task_date = date.today()
            elif isinstance(due_at, str) and len(due_at) >= 10:
                try:
                    task_date = date.fromisoformat(due_at[:10])
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

        # policz numer LIVE w obrębie daty zadania (jak w `lista`)
        if tid is not None:
            tasks_for_day = _sort_for_list(tasks_mod.list_tasks_for_date(task_date) or [])
            for idx, t in enumerate(tasks_for_day, start=1):
                try:
                    if int(t.get("id")) == tid:
                        title = str(t.get("title") or "(bez tytułu)").strip()
                        return _as_reply("add_task", f"✅ Dodane zadanie #{idx}: {title} (na {_label_for_date(task_date)})")
                except Exception:
                    continue

        # jeśli nie umiemy policzyć LIVE, wróć do oryginalnej odpowiedzi
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

    return _as_reply("unknown", "Nie mam jeszcze tej komendy. Spróbuj: `lista`, `dodaj: ...`, `usuń ...`, `priorytet ...`.")
