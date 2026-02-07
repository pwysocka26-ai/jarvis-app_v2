from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.security import auth_dependency
from app.config import get_ollama_model


router = APIRouter(prefix="/v1", tags=["model"])


class ModelState(BaseModel):
    model: str = Field(..., description="Ollama model name, e.g. llama3, mistral")


@router.get("/model")
def get_model(_: None = Depends(auth_dependency)) -> ModelState:
    return ModelState(model=get_ollama_model())


@router.post("/model")
def set_model(payload: ModelState, _: None = Depends(auth_dependency)) -> ModelState:
    # Model is fixed in this build. We keep the endpoint for compatibility,
    # but we do not allow changing it at runtime.
    return ModelState(model=get_ollama_model())
