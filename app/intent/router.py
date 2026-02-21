from __future__ import annotations

from typing import Any, Dict, Optional

import re

from app.b2c import tasks as tasks_mod
from app.b2c.travel_mode import morning_brief
from datetime import date

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
            or t.startswith("rano")
            or t.startswith("diag")
            or t.startswith("help")
        )

    # 1) Delete task: "usuń 3"
    m = re.search(r"^(?:usun|usuń)\s+(\d+)\s*$", low)
    if m:
        task_id = int(m.group(1))
        # tasks module API
        out = tasks_mod.delete_task_by_id(task_id)
        return _as_reply("delete_task", _reply_from_any(out, default=f"🗑 Usunięto zadanie #{task_id}."))
    elif low.startswith("usuń") or low.startswith("usun"):
        return _as_reply("delete_task", "Podaj ID zadania, np: 'usuń 3'.")

    # 1b) List tasks for today: "lista"
    if low in {"lista", "list"}:
        tasks = tasks_mod.list_tasks_for_date(date.today())
        if not tasks:
            return _as_reply("list_tasks", "Brak zaplanowanych zadań na dziś.")

        lines = ["**Najważniejsze dziś:**"]
        for t in tasks:
            if not isinstance(t, dict):
                continue
            tid = t.get("id")
            title = str(t.get("title") or "(bez tytułu)").strip()
            loc = str(t.get("location") or "").strip()
            time_s = str(t.get("time") or "").strip()
            when = f"{time_s} — " if time_s else ""

            # Meta: priority + duration
            meta = []
            try:
                pr = int(t.get("priority")) if t.get("priority") is not None else None
            except Exception:
                pr = None
            if pr:
                meta.append(f"p{pr}")

            dur = t.get("duration_min")
            if dur is None:
                dur = t.get("duration")
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
            prefix = f"#{tid} " if tid is not None else ""
            lines.append(f"• {prefix}{when}{title}{meta_s}{tail}")

        return _as_reply("list_tasks", "\n".join(lines))

    # 2) Pending reminder FIRST
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

        # Don't block other intents. If user types something else, continue routing.
        if not _is_command_like(message):
            return _as_reply("set_reminder", f"Ustawić przypomnienie na **{reminder_at}**? (tak/nie)")

    # 3) Pending travel
    pending_t = tasks_mod.get_pending_travel()
    if pending_t:
        # Consume only if message is a valid travel choice; otherwise allow other commands.
        out = tasks_mod.apply_travel_mode_to_pending(message)
        if out is not None:
            return _as_reply("set_travel_mode", _reply_from_any(out, default="OK"))

        if not _is_command_like(message):
            return _as_reply("set_travel_mode", "Jak jedziesz? Napisz: 'samochodem' / 'komunikacją' / 'rowerem' / 'pieszo'.")

    # 4) Add task
    if low.startswith("dodaj:") or low.startswith("dodaj "):
        out = tasks_mod.add_task(message)
        return _as_reply("add_task", _reply_from_any(out))

    # 5) Morning
    if low in {"rano", "dzień dobry", "dzien dobry", "poranek"}:
        out = morning_brief()
        if isinstance(out, dict) and ("reply" in out or "response" in out):
            text = out.get("response") or out.get("reply")
            return {"intent": out.get("intent", "morning_brief"), "reply": text, "response": text, **{k: v for k, v in out.items() if k not in {"reply", "response"}}}
        return _as_reply("morning_brief", str(out))

    return _as_reply("unknown", "Nie mam jeszcze tej komendy. Spróbuj: 'rano' albo 'dodaj: ...'")
