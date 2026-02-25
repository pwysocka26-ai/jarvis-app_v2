from app.intent.router import route_intent

def handle_chat(message: str, mode: str = "b2c") -> str:
    # Compatibility: router implementations may accept `mode=` or only `persona=`.
    try:
        return route_intent(message, mode=mode)
    except TypeError:
        # Older router signature: route_intent(message, persona="b2c")
        return route_intent(message, persona=mode)
