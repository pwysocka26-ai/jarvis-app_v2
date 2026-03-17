
from __future__ import annotations

from fastapi import FastAPI
from app.api.mobile import router as mobile_router

app = FastAPI(title="Jarvis Mobile API", version="v1")
app.include_router(mobile_router)
