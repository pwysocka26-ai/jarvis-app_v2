from fastapi import APIRouter
from typing import Any, Dict, List

router = APIRouter(prefix="/v1/admin", tags=["admin"])

@router.get("/audit")
def list_audit() -> Dict[str, Any]:
    # Minimal stub for contract parity
    return {"events": []}

@router.get("/audit/{event_id}")
def get_audit_event(event_id: str) -> Dict[str, Any]:
    return {"event_id": event_id, "ok": True}
