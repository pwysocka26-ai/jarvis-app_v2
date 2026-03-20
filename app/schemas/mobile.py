from __future__ import annotations

from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


class MobileHealthResponse(BaseModel):
    status: str
    product: str
    version: str


class InboxCreateRequest(BaseModel):
    text: str


class MobileActionResponse(BaseModel):
    status: str
    intent: Optional[str] = None
    message: str
    changed: bool = False


class FreeWindow(BaseModel):
    start: str
    end: str


class TimeBlock(BaseModel):
    start: str
    end: str
    label: str


class PriorityItem(BaseModel):
    title: str
    category: str
    priority: int
    time: Optional[str] = None
    kind: Literal["event", "task"]


class TimelineItem(BaseModel):
    id: str
    kind: Literal["event", "task", "focus", "break", "lunch"]
    title: str
    start: str
    end: str
    location: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None


class DaySummary(BaseModel):
    next_item: Optional[str] = None
    next_time: Optional[str] = None
    status: Literal["ok", "warning", "empty"]


class DayScreenPayload(BaseModel):
    date: str
    summary: DaySummary
    timeline: List[TimelineItem]
    free_windows: List[FreeWindow]
    time_blocks: List[TimeBlock]
    priorities: List[PriorityItem]


class MobileAiChatRequest(BaseModel):
    message: str = Field(min_length=1)
    model: Optional[str] = None
    conversation_tail: List[dict[str, Any]] = Field(default_factory=list)
    local_brain_notes: List[dict[str, Any]] = Field(default_factory=list)


class MobileAiChatResponse(BaseModel):
    status: str
    reply: str
    actions: List[dict[str, Any]] = Field(default_factory=list)
    model: Optional[str] = None
    source: str = "ollama"


class MobileAiHealthResponse(BaseModel):
    status: str
    available: bool
    model: str
    base_url: str
    source: str = "ollama"
