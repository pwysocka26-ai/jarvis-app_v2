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
    actions: List[dict[str, Any]] = Field(default_factory=list)


class InboxRow(BaseModel):
    id: int
    text: str
    kind: str


class InboxListResponse(BaseModel):
    status: str
    shopping: List[InboxRow] = Field(default_factory=list)
    unscheduled: List[InboxRow] = Field(default_factory=list)


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
    checklist_count: int = 0


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


class MobileChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_tail: List[dict[str, Any]] = Field(default_factory=list)


class ShoppingConfirmRequest(BaseModel):
    event_text: str
    selected_item_ids: List[int] = Field(default_factory=list)
    extra_items: List[str] = Field(default_factory=list)


class ChecklistAddRequest(BaseModel):
    text: str


class ChecklistItem(BaseModel):
    index: int
    text: str
    done: bool = False


class PlanTaskDetail(BaseModel):
    task_id: int
    title: str
    due_at: str
    category: str
    checklist: List[ChecklistItem] = Field(default_factory=list)


class PlanTaskDetailResponse(BaseModel):
    status: str
    message: str
    task: Optional[PlanTaskDetail] = None


class ShoppingTaskSummary(BaseModel):
    task_id: int
    title: str
    due_at: str


class ShoppingTaskListResponse(BaseModel):
    status: str
    tasks: List[ShoppingTaskSummary] = Field(default_factory=list)


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
