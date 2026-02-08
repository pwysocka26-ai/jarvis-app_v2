from fastapi import Header, HTTPException
from .entra_jwt import validate_bearer_token, AuthError, Actor

def get_actor(authorization: str | None = Header(default=None)) -> Actor:
    """Dependency for endpoints: returns Actor or raises 401."""
    try:
        return validate_bearer_token(authorization or "")
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")
