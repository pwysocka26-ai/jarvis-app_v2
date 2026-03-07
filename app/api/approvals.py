from fastapi import APIRouter
from typing import Any, Dict

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])

# Minimal contract endpoints for openapi.yaml route parity.
# These endpoints are intentionally lightweight and non-breaking.

@router.get("/{approval_id}")
def get_approval(approval_id: str) -> Dict[str, Any]:
    return {"approval_id": approval_id, "status": "pending"}

@router.post("/{approval_id}/decision")
def post_approval_decision(approval_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    decision = payload.get("decision") or payload.get("action") or "unknown"
    return {"approval_id": approval_id, "decision": decision, "ok": True}
