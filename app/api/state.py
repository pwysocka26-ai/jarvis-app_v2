from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

"""State/health API.

NOTE: Auth dependency lives in `app.api.security` (single source of truth).
Historically some modules imported a private `_auth` from `app.api.chat`.
That made tests/production brittle when the chat module was refactored.
"""

from app.api.security import auth_dependency as _auth
from app.daily_state.service import get_day_state, set_day_state

router = APIRouter(prefix="/v1", tags=["state"])

DayState = Literal["morning", "day", "evening", "chaos"]


class SetStateRequest(BaseModel):
    state: DayState = Field(..., description="One of: morning/day/evening/chaos")
    user_id: str = Field(default="default", description="User id (default: 'default')")


class StateResponse(BaseModel):
    user_id: str
    state: DayState
    updated_at: datetime


@router.get("/state", response_model=StateResponse)
def get_state(user_id: str = "default", _: None = Depends(_auth)) -> StateResponse:
    st, ts = get_day_state(user_id, with_ts=True)
    return StateResponse(user_id=user_id, state=st, updated_at=ts)


@router.post("/state", response_model=StateResponse)
def set_state(req: SetStateRequest, _: None = Depends(_auth)) -> StateResponse:
    ts = set_day_state(req.user_id, req.state)
    return StateResponse(user_id=req.user_id, state=req.state, updated_at=ts)
