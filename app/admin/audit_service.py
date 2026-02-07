from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models import AuditEvent

def query_audit(
    db: Session,
    limit: int = 50,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[datetime] = None,
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit)
    if actor:
        stmt = stmt.where(AuditEvent.actor == actor)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if since:
        stmt = stmt.where(AuditEvent.timestamp >= since)
    return list(db.execute(stmt).scalars().all())
