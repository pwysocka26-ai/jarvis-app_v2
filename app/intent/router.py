from __future__ import annotations

from typing import Any, Dict, Optional

from app.b2c import tasks as tasks_mod
from app.b2c.travel_mode import morning_brief

def route_intent( message: str, persona: str = "b2c", mode: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    msg = (message or "").strip()
    low = msg.lower()

    # 0) If we are waiting for travel mode answer – handle it FIRST (prevents "bełkot")
    pending = tasks_mod.get_pending_travel()
    if pending:
        tm = tasks_mod.parse_travel_mode(low)
        if tm:
            out = tasks_mod.apply_travel_mode_to_task_id(tm, int(pending["task_id"]))
            tasks_mod.clear_pending_travel()
            reply = out.get("reply", "OK")
            return {"intent": "set_travel_mode", "reply": reply, "response": reply}
        else:
            reply = "Nie złapałem sposobu dojazdu. Napisz: `samochodem` / `rowerem` / `pieszo` / `komunikacją`."
            return {"intent": "set_travel_mode", "reply": reply, "response": reply}

    # 1) Morning flow
    if low in {"rano", "dzień dobry", "dzien dobry"}:
        return morning_brief()

    # 2) Add task
    if low.startswith("dodaj:") or low.startswith("dodaj "):
        raw = msg.split(":", 1)[1].strip() if ":" in msg else msg[len("dodaj"):].strip()
        out = tasks_mod.add_task(raw)
        reply = out.get("reply", "✅ Dodane.")
        return {"intent": "add_task", "reply": reply, "response": reply}

    # 3) Help / fallback (NO LLM here – to avoid random chat)
    reply = (
        "Nie mam jeszcze tego ogarniętego w trybie b2c 😅\n"
        "Użyj proszę jednej z komend:\n"
        "• `dodaj: ...` (np. `dodaj: dentysta dziś 19:00, Niemcewicza 25, Warszawa`)\n"
        "• `rano` (plan dnia + sugerowana godzina wyjścia)\n"
        "Jeśli chcesz, mogę dodać kolejne intencje."
    )
    return {"intent": "unknown", "reply": reply, "response": reply}