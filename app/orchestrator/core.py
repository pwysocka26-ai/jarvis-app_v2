from __future__ import annotations

from typing import Any, Dict

from app.intent.router import route_intent

def handle_chat(message: str, *, mode: str | None = None) -> Dict[str, Any]:
    return route_intent(message, mode=mode)
    
import app.intent.router
print("### core.py uses intent.router FILE ###", app.intent.router.__file__)
