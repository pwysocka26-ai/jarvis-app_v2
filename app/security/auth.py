# -*- coding: utf-8 -*-
"""
DEV bearer-token authentication helper.

Optional utility; some branches of the codebase might import it.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException, status

EXPECTED_TOKEN = os.getenv("API_TOKEN", "dev-token")


def require_dev_bearer(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> str:
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    if token != EXPECTED_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing/invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
