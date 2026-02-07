from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class ChatRequest(BaseModel):
    message: str = Field(..., description="Message from user")
    mode: Optional[str] = Field(
        default=None,
        description='Session mode: "b2c" (default) or "pro"',
    )

class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    meta: Dict[str, Any] = {}
