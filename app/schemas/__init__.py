from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(default="")
    mode: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


__all__ = ["ChatRequest", "ChatResponse"]
