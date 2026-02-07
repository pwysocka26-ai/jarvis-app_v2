from __future__ import annotations

from fastapi import FastAPI
from app.api.chat import router as chat_router

app = FastAPI(title="Jarvis API", version="0.1.0")
app.include_router(chat_router)

@app.get("/health")
def health():
    return {"ok": True}
