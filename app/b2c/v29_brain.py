
from __future__ import annotations

from datetime import date
from typing import Optional


def _safe_call(fn, fallback: str) -> str:
    try:
        return fn()
    except Exception:
        return fallback


def command_center(tasks_mod, origin: Optional[str], default_mode: Optional[str], buffer_min: int = 10) -> str:
    sections = [f"COMMAND CENTER — {date.today().isoformat()}", ""]

    try:
        from app.b2c.context_ai import auto_plan_day
        plan = auto_plan_day(tasks_mod, origin, default_mode, buffer_min=buffer_min)
    except Exception:
        plan = "Nie mogę teraz zbudować planu dnia."
    sections.extend(["PLAN DNIA", plan, ""])

    try:
        from app.b2c.v25_brain import focus_status
        focus = focus_status()
    except Exception:
        focus = "Nie mogę teraz sprawdzić fokusu."
    sections.extend(["FOCUS", focus, ""])

    try:
        from app.b2c.v26_brain import context_summary
        context = context_summary()
    except Exception:
        context = "Nie mogę teraz pokazać kontekstu."
    sections.extend(["KONTEKST", context, ""])

    try:
        from app.b2c.v24_brain import inbox_brain_summary
        inbox = inbox_brain_summary(tasks_mod)
    except Exception:
        inbox = "Nie mogę teraz przygotować przeglądu inboxa."
    sections.extend(["INBOX", inbox, ""])

    try:
        from app.b2c.context_ai import daily_next_step
        suggestion = daily_next_step(tasks_mod, origin, default_mode, buffer_min=buffer_min)
    except Exception:
        suggestion = "Nie mogę teraz wskazać następnego kroku."
    sections.extend(["SUGESTIA", suggestion, ""])

    try:
        from app.b2c.v28_brain import self_optimizing_brain
        optimization = self_optimizing_brain(tasks_mod)
    except Exception:
        optimization = "Nie mogę teraz przygotować sugestii optymalizacji."
    sections.extend(["OPTYMALIZACJA", optimization])

    return "\n".join(sections)
