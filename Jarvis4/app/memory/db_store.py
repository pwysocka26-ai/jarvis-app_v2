from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import UserFact, ChatMessage


class DBMemoryStore:
    """Persistent memory backed by SQL database (Postgres/SQLite).

    Mirrors the interface of MemoryStore so it can be swapped via MEMORY_BACKEND.
    """

    def __init__(self, user_id: str = "default", max_history: int = 50, history_limit: Optional[int] = None):
        self.user_id = user_id
        self.max_history = max_history
        self.history_limit = history_limit or max_history

    def _db(self) -> Session:
        return SessionLocal()

    def load_history(self) -> List[Dict[str, str]]:
        db = self._db()
        try:
            q = (
                select(ChatMessage)
                .where(ChatMessage.user_id == self.user_id)
                .order_by(ChatMessage.id.desc())
                .limit(int(self.history_limit))
            )
            rows = list(db.scalars(q))
            rows.reverse()
            return [{"role": r.role, "content": r.content} for r in rows]
        finally:
            db.close()

    def save_history(self, history: List[Dict[str, str]]) -> None:
        # Not used; we append messages incrementally.
        return

    def append_message(self, role: str, content: str) -> None:
        db = self._db()
        try:
            db.add(ChatMessage(user_id=self.user_id, role=role, content=content))
            db.commit()
            # Trim old
            q_ids = (
                select(ChatMessage.id)
                .where(ChatMessage.user_id == self.user_id)
                .order_by(ChatMessage.id.desc())
                .offset(int(self.max_history))
            )
            old_ids = [rid for (rid,) in db.execute(q_ids).all()]
            if old_ids:
                db.execute(delete(ChatMessage).where(ChatMessage.id.in_(old_ids)))
                db.commit()
        finally:
            db.close()

    def load_facts(self) -> Dict[str, Any]:
        db = self._db()
        try:
            q = select(UserFact).where(UserFact.user_id == self.user_id, UserFact.status == "active")
            rows = list(db.scalars(q))
            facts: Dict[str, Any] = {}
            for r in rows:
                facts[r.key] = r.value
            return facts
        finally:
            db.close()

    def save_facts(self, facts: Dict[str, Any]) -> None:
        # Not used; facts are upserted per key.
        return

    def remember_fact(self, key: str, value: Any, source: str = "user_explicit", confidence: float = 1.0, importance: int = 80) -> None:
        db = self._db()
        try:
            # soft-supersede previous
            prev = db.scalars(select(UserFact).where(UserFact.user_id == self.user_id, UserFact.key == key, UserFact.status == "active")).first()
            if prev:
                prev.status = "superseded"
                prev.updated_at = datetime.utcnow()
            db.add(
                UserFact(
                    user_id=self.user_id,
                    key=key,
                    value=value,
                    source=source,
                    confidence=float(confidence),
                    importance=int(importance),
                    status="active",
                )
            )
            db.commit()
        finally:
            db.close()

    def forget_fact(self, key: str) -> bool:
        db = self._db()
        try:
            row = db.scalars(select(UserFact).where(UserFact.user_id == self.user_id, UserFact.key == key, UserFact.status == "active")).first()
            if not row:
                return False
            row.status = "deleted"
            row.updated_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            db.close()
