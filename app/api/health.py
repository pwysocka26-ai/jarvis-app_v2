from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/health")
def health(request: Request):
    # Ensure ids are always present (middleware should set them).
    request_id = getattr(request.state, "request_id", None) or "unknown"
    trace_id = getattr(request.state, "trace_id", None) or "unknown"
    return {"ok": True, "request_id": request_id, "trace_id": trace_id}
