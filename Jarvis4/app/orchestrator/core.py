from __future__ import annotations

from typing import Any, Dict

from app.intent.router import route_intent

def handle_chat(message: str, *, mode: str | None = None) -> Dict[str, Any]:
    return route_intent(message, mode=mode)
