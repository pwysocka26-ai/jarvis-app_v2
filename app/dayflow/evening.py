from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.b2c.tasks import _load  # internal ok for MVP


def evening_summary() -> Dict[str, Any]:
    data = _load()
    tasks = data.get("tasks", [])
    today = datetime.now().date()

    done_today = []
    pending = []

    for t in tasks:
        if t.get("done"):
            done_at = t.get("done_at")
            try:
                dt = datetime.fromisoformat(done_at) if done_at else None
            except Exception:
                dt = None
            if dt and dt.date() == today:
                done_today.append(t)
        else:
            pending.append(t)

    lines: List[str] = []
    lines.append("Wieczór 🙂 Zróbmy krótkie domknięcie dnia.")
    lines.append("")

    if done_today:
        lines.append("**Dziś zrobione:**")
        for t in done_today[:8]:
            lines.append(f"✔ {t.get('title','')}")
    else:
        lines.append("**Dziś zrobione:** (brak odhaczonych zadań)")

    if pending:
        lines.append("")
        lines.append("**Zostaje na jutro / do przeniesienia:**")
        for t in pending[:8]:
            lines.append(f"☐ {t.get('title','')}")

    lines.append("")
    lines.append("Zaczynamy od pierwszego kroku: **wybierz 1 rzecz do przeniesienia na jutro** — potwierdzasz?")

    return {"response": "\n".join(lines), "intent": "dayflow_evening"}
