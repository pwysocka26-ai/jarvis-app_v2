from __future__ import annotations

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

    # ---------------------------------------------------------------------
    # Public API expected by app.intent.router (mirrors MemoryStore)
    # ---------------------------------------------------------------------

    def remember_fact(self, fact: str) -> None:
        """Remember a single free-form fact.

        The file backend stores free-form facts as a list (items). For the DB
        backend we store each item as a separate row in UserFact.
        """
        fact = (fact or "").strip()
        if not fact:
            return
        self._upsert_fact(key=fact, value=True, source="user_explicit", confidence=1.0, importance=80)

    def forget_fact(self, fact: str) -> None:
        """Forget a single free-form fact (soft delete)."""
        fact = (fact or "").strip()
        if not fact:
            return
        self._mark_fact_deleted(key=fact)

    def list_facts(self) -> List[str]:
        """List remembered free-form facts (excluding KV entries)."""
        db = self._db()
        try:
            q = select(UserFact.key).where(
                UserFact.user_id == self.user_id,
                UserFact.status == "active",
            )
            keys = [k for (k,) in db.execute(q).all()]
            return [k for k in keys if not str(k).startswith("kv:")]
        finally:
            db.close()

    # --------- DANE STRUKTURALNE (KV) ---------

    def set_kv(self, key: str, value: Any) -> None:
        key = (key or "").strip()
        if not key:
            return
        self._upsert_fact(key=f"kv:{key}", value=value, source="kv", confidence=1.0, importance=90)

    def get_kv(self, key: str, default: Any = None) -> Any:
        key = (key or "").strip()
        if not key:
            return default
        db = self._db()
        try:
            row = db.scalars(
                select(UserFact).where(
                    UserFact.user_id == self.user_id,
                    UserFact.key == f"kv:{key}",
                    UserFact.status == "active",
                )
            ).first()
            return row.value if row else default
        finally:
            db.close()

    def delete_kv(self, key: str) -> None:
        key = (key or "").strip()
        if not key:
            return
        self._mark_fact_deleted(key=f"kv:{key}")

    def all_kv(self) -> Dict[str, Any]:
        db = self._db()
        try:
            q = select(UserFact).where(
                UserFact.user_id == self.user_id,
                UserFact.status == "active",
            )
            rows = list(db.scalars(q))
            out: Dict[str, Any] = {}
            for r in rows:
                k = str(r.key)
                if k.startswith("kv:"):
                    out[k[3:]] = r.value
            return out
        finally:
            db.close()

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _upsert_fact(
        self,
        *,
        key: str,
        value: Any,
        source: str = "user_explicit",
        confidence: float = 1.0,
        importance: int = 80,
    ) -> None:
        db = self._db()
        try:
            prev = db.scalars(
                select(UserFact).where(
                    UserFact.user_id == self.user_id,
                    UserFact.key == key,
                    UserFact.status == "active",
                )
            ).first()
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

    def _mark_fact_deleted(self, *, key: str) -> bool:
        db = self._db()
        try:
            row = db.scalars(
                select(UserFact).where(
                    UserFact.user_id == self.user_id,
                    UserFact.key == key,
                    UserFact.status == "active",
                )
            ).first()
            if not row:
                return False
            row.status = "deleted"
            row.updated_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            db.close()
