import json
from sqlalchemy.orm import Session
from .models import AuditEvent
from typing import Optional

def write_audit(
    db: Session,
    actor: str,
    action: str,
    payload: dict,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> int:
    enriched = {
        **payload,
        "_request_id": request_id,
        "_trace_id": trace_id,
    }
    evt = AuditEvent(actor=actor, action=action, payload_json=json.dumps(enriched, ensure_ascii=False))
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt.id
