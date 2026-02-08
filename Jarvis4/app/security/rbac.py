from app.security.entra_jwt import Actor

class Forbidden(RuntimeError):
    pass

def require_any_role(actor: Actor, allowed: list[str]):
    if not allowed:
        return
    if any(r in actor.roles for r in allowed):
        return
    raise Forbidden(f"Missing required role. Allowed: {allowed}")
