from __future__ import annotations

import os
import re
import traceback
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings
from app.schemas import ChatRequest, ChatResponse
from app.orchestrator.core import handle_chat

router = APIRouter(prefix="/v1", tags=["chat"])

# -----------------------------------------------------------------------------
# Diagnostics toggles (set as environment variables)
#
#   JARVIS_DIAG=1        -> prints HIT + OUT summary (safe, recommended)
#   JARVIS_STACK=1       -> prints Python stack trace on each /v1/chat request
#   JARVIS_TRACE_RAISE=1 -> raises RuntimeError("TRACE ME") after handle_chat
#
# Examples (PowerShell):
#   $env:JARVIS_DIAG="1"
#   $env:JARVIS_STACK="1"
#   $env:JARVIS_TRACE_RAISE="1"
# -----------------------------------------------------------------------------
DIAG = os.getenv("JARVIS_DIAG", "").strip() == "1"
STACK = os.getenv("JARVIS_STACK", "").strip() == "1"
TRACE_RAISE = os.getenv("JARVIS_TRACE_RAISE", "").strip() == "1"

print("### LOADED app/api/chat.py ###", __file__, "| DIAG=", DIAG, "| STACK=", STACK, "| RAISE=", TRACE_RAISE)


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


def _head(s: Any, n: int = 160) -> str:
    """Safe preview helper for debug printing."""
    if s is None:
        return ""
    try:
        txt = str(s)
    except Exception:
        return "<unprintable>"
    txt = txt.replace("\r", " ").replace("\n", "\\n")
    return txt[:n]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, _: None = Depends(_auth)) -> ChatResponse:
    if DIAG:
        print("\n### HIT /v1/chat ###", __file__)
        print("### REQ ### message_head=", _head(req.message, 120), "| mode=", req.mode)

    out = handle_chat(req.message, mode=req.mode)

    if DIAG:
        try:
            keys = list(out.keys()) if isinstance(out, dict) else ["<not a dict>"]
        except Exception:
            keys = ["<keys error>"]
        print("### OUT TYPE ###", type(out))
        print("### OUT KEYS ###", keys)
        if isinstance(out, dict):
            print("### OUT INTENT ###", out.get("intent"))
            print("### OUT REPLY HEAD ###", _head(out.get("reply"), 200))
            print("### OUT RESPONSE HEAD ###", _head(out.get("response"), 200))

    if STACK:
        print("\n### STACK TRACE (/v1/chat) ###")
        traceback.print_stack()

    if TRACE_RAISE:
        # Use only temporarily to force a visible error + traceback in server console.
        raise RuntimeError("TRACE ME")

    # NOTE: CLI typically uses `reply`, but we keep `meta` with everything else
    # so you can inspect `response` etc.
    reply = out.get("reply", "") if isinstance(out, dict) else ""
    intent = out.get("intent") if isinstance(out, dict) else None
    meta = {k: v for k, v in out.items() if k not in ("reply", "intent")} if isinstance(out, dict) else {}

    return ChatResponse(reply=reply, intent=intent, meta=meta)