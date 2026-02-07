from __future__ import annotations

"""Very simple dev authentication.

This project is currently a local/offline demo, so we keep auth minimal:
- Client provides token via `X-API-Token` header or `Authorization: Bearer <token>`.
- Token is compared against `settings.api_token`.

In cloud deployments you should replace this with proper auth (OAuth/JWT/etc.).
"""

from fastapi import Header, HTTPException

import re


def _clean_token(token: str | None) -> str:
    if token is None:
        return ""
    t = token.strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    return t

from app.config import settings


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def verify_token(
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    token = (x_api_token or "").strip() or (_extract_bearer(authorization) or "").strip()
    if not token or token != settings.api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")


# Backwards compatible name used by some modules
def auth_dependency(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
) -> None:
    """Alias for verify_token (kept for compatibility)."""
    verify_token(x_api_token=x_api_token, authorization=authorization)
