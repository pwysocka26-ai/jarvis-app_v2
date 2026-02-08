from __future__ import annotations

from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.db import init_db

app = FastAPI(title="Jarvis API", version="0.1.0")
app.include_router(chat_router)

@app.on_event("startup")
def _startup():
    # Ensures tables exist for SQLite / local DB.
    init_db()

@app.get("/health")
def health():
    return {"ok": True}
