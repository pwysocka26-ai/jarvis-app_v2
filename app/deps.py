from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import Settings


@lru_cache
def get_settings() -> Settings:
    """Central place for loading settings (env vars) with caching.

    This enables dependency injection + easy overriding in tests.
    """
    return Settings()


class AuthContext(BaseModel):
    token_present: bool = False


def get_auth(
    settings: Settings = Depends(get_settings),
    x_api_token: Optional[str] = Header(default=None, alias="X-API-Token"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> AuthContext:
    """Auth dependency.

    - If API_TOKEN is set (settings.api_token), requests must provide:
      - header: X-API-Token: <token>  OR
      - header: Authorization: Bearer <token>

    - If API_TOKEN is empty/None, auth is disabled (useful for local dev).
    """
    expected = getattr(settings, "api_token", None)
    if not expected:
        return AuthContext(token_present=False)

    provided = x_api_token
    if not provided and authorization:
        m = authorization.strip().split()
        if len(m) == 2 and m[0].lower() == "bearer":
            provided = m[1]

    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return AuthContext(token_present=True)
