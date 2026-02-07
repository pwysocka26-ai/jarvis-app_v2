from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Header, HTTPException
from app.config import settings
from app.schemas import ChatRequest, ChatResponse
from app.orchestrator.core import handle_chat

router = APIRouter(prefix="/v1", tags=["chat"])


def _clean_token(token: str | None) -> str:
    if not token:
        return ""
    t = token.strip()
    # handle accidental quotes pasted from PowerShell/docs
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    return t

def _auth(
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Simple shared-secret auth for local dev.

    Accepts either:
    - X-API-Token: <token>
    - Authorization: Bearer <token>

    If settings.api_token is empty, auth is disabled.
    """
    expected = _clean_token(settings.api_token)
    if not expected:
        return

    got = _clean_token(x_api_token)
    if not got and authorization:
        m = re.match(r"^Bearer\s+(.+)$", authorization.strip(), flags=re.IGNORECASE)
        if m:
            got = _clean_token(m.group(1))

    if got != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, _: None = Depends(_auth)) -> ChatResponse:
    out = handle_chat(req.message, mode=req.mode)
    return ChatResponse(reply=out.get("reply",""), intent=out.get("intent"), meta={k:v for k,v in out.items() if k not in ("reply","intent")})
