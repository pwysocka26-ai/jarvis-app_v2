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


class InboxListItem(BaseModel):
    id: int
    text: str
    kind: str


class InboxListResponse(BaseModel):
    status: str
    shopping: List[InboxListItem] = Field(default_factory=list)
    unscheduled: List[InboxListItem] = Field(default_factory=list)


class ShoppingConfirmRequest(BaseModel):
    event_text: str
    selected_item_ids: List[int] = Field(default_factory=list)
    extra_items: List[str] = Field(default_factory=list)


class MobileChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_tail: List[dict[str, Any]] = Field(default_factory=list)


class MobileChatResponse(BaseModel):
    status: str
    intent: Optional[str] = None
    reply: str
    actions: List[dict[str, Any]] = Field(default_factory=list)
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
    task_id: Optional[int] = None
    deletable: bool = False


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
