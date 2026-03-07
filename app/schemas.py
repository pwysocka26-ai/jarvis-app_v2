from __future__ import annotations

from pydantic import BaseModel, Field, AliasChoices
from datetime import datetime, date
from typing import Any, Dict, Optional, List

class ChatRequest(BaseModel):
    # Accept both `message` and legacy `text` for backwards compatibility.
    message: str = Field(
        ...,
        description="Message from user",
        min_length=1,
        max_length=5000,
        validation_alias=AliasChoices("message", "text"),
    )
    mode: Optional[str] = Field(
        default=None,
        description='Session mode: "b2c" (default) or "pro"',
    )

class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    meta: Dict[str, Any] = {}

class PlanItemCreate(BaseModel):
    day: date
    type: str = "chore"
    title: str
    start_time: Optional[datetime] = None
    location: Optional[str] = None
    priority: int = 50
    notes: Optional[str] = None
    mode: Optional[str] = "b2c"


class PlanItemOut(BaseModel):
    id: int
    type: str
    title: str
    start_time: Optional[datetime] = None
    location: Optional[str] = None
    priority: int
    notes: Optional[str] = None


class DayPlanOut(BaseModel):
    day: date
    summary: Optional[str] = None
    items: List[PlanItemOut] = []
