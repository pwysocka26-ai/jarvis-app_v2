from __future__ import annotations

from fastapi import APIRouter

from app.schemas.mobile import (
    InboxCreateRequest,
    MobileActionResponse,
    MobileHealthResponse,
    DayScreenPayload,
    MobileAiChatRequest,
    MobileAiChatResponse,
    MobileAiHealthResponse,
)
from app.services.mobile_service import (
    build_day_payload,
    create_inbox_item,
    get_memory,
    get_priorities_tomorrow,
    health,
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


@router.post("/inbox", response_model=MobileActionResponse)
def mobile_inbox(req: InboxCreateRequest) -> MobileActionResponse:
    return MobileActionResponse(**create_inbox_item(req.text))


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
