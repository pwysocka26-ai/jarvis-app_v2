from __future__ import annotations

from datetime import datetime
from typing import Tuple, overload, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import UserDayState

DayState = Literal["morning", "day", "evening", "chaos"]


def _db() -> Session:
    return SessionLocal()


@overload
def get_day_state(user_id: str = "default", with_ts: Literal[False] = False) -> DayState: ...
@overload
def get_day_state(user_id: str = "default", with_ts: Literal[True] = True) -> Tuple[DayState, datetime]: ...


def get_day_state(user_id: str = "default", with_ts: bool = False):
    db = _db()
    try:
        row = db.scalars(select(UserDayState).where(UserDayState.user_id == user_id)).first()
        if not row:
            if with_ts:
                return "day", datetime.utcnow()
            return "day"
        if with_ts:
            return row.state, row.updated_at
        return row.state
    finally:
        db.close()


def set_day_state(user_id: str, state: DayState) -> datetime:
    user_id = (user_id or "default").strip() or "default"
    db = _db()
    try:
        row = db.scalars(select(UserDayState).where(UserDayState.user_id == user_id)).first()
        now = datetime.utcnow()
        if row:
            row.state = state
            row.updated_at = now
        else:
            row = UserDayState(user_id=user_id, state=state, updated_at=now)
            db.add(row)
        db.commit()
        return now
    finally:
        db.close()
