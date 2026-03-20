from __future__ import annotations

from fastapi import APIRouter

from app.schemas.mobile import (
    InboxCreateRequest,
    InboxListResponse,
    MobileActionResponse,
    MobileHealthResponse,
    DayScreenPayload,
    MobileAiChatRequest,
    MobileAiChatResponse,
    MobileAiHealthResponse,
    MobileChatRequest,
    MobileChatResponse,
    ShoppingConfirmRequest,
)
from app.services.mobile_service import (
    build_day_payload,
    chat_command,
    clear_day_tasks,
    confirm_shopping_event,
    create_inbox_item,
    delete_plan_task,
    get_memory,
    get_priorities_tomorrow,
    health,
    list_inbox_items,
    plan_tomorrow,
    ollama_chat,
    ollama_health,
)

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/health", response_model=MobileHealthResponse)
def mobile_health() -> MobileHealthResponse:
    return MobileHealthResponse(**health())


@router.get("/today", response_model=DayScreenPayload)
def mobile_today() -> DayScreenPayload:
    return DayScreenPayload(**build_day_payload(day_offset=0))


@router.get("/tomorrow", response_model=DayScreenPayload)
def mobile_tomorrow() -> DayScreenPayload:
    return DayScreenPayload(**build_day_payload(day_offset=1))


@router.get("/inbox/list", response_model=InboxListResponse)
def mobile_inbox_list() -> InboxListResponse:
    return InboxListResponse(**list_inbox_items())


@router.post("/inbox", response_model=MobileActionResponse)
def mobile_inbox(req: InboxCreateRequest) -> MobileActionResponse:
    return MobileActionResponse(**create_inbox_item(req.text))


@router.post("/chat", response_model=MobileChatResponse)
def mobile_chat(req: MobileChatRequest) -> MobileChatResponse:
    return MobileChatResponse(**chat_command(req.message, conversation_tail=req.conversation_tail))


@router.post("/shopping/confirm", response_model=MobileActionResponse)
def mobile_shopping_confirm(req: ShoppingConfirmRequest) -> MobileActionResponse:
    return MobileActionResponse(**confirm_shopping_event(
        event_text=req.event_text,
        selected_item_ids=req.selected_item_ids,
        extra_items=req.extra_items,
    ))


@router.delete("/plan/task/{task_id}", response_model=MobileActionResponse)
def mobile_delete_task(task_id: int) -> MobileActionResponse:
    return MobileActionResponse(**delete_plan_task(task_id))


@router.delete("/plan/day/{target_date}", response_model=MobileActionResponse)
def mobile_clear_day(target_date: str) -> MobileActionResponse:
    return MobileActionResponse(**clear_day_tasks(target_date))


@router.post("/plan/tomorrow", response_model=MobileActionResponse)
def mobile_plan_tomorrow() -> MobileActionResponse:
    return MobileActionResponse(**plan_tomorrow())


@router.get("/memory")
def mobile_memory():
    return get_memory()


@router.get("/priorities/tomorrow")
def mobile_priorities_tomorrow():
    return get_priorities_tomorrow()


@router.get("/ai/health", response_model=MobileAiHealthResponse)
def mobile_ai_health(model: str | None = None) -> MobileAiHealthResponse:
    return MobileAiHealthResponse(**ollama_health(model=model))


@router.post("/ai/chat", response_model=MobileAiChatResponse)
def mobile_ai_chat(req: MobileAiChatRequest) -> MobileAiChatResponse:
    return MobileAiChatResponse(**ollama_chat(
        message=req.message,
        model=req.model,
        conversation_tail=req.conversation_tail,
        local_brain_notes=req.local_brain_notes,
    ))
