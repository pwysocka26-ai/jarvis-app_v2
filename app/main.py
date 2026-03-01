from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.chat import router as chat_router
from app.api.state import router as state_router
from app.api.plan import router as plan_router
from app.api.diag import router as diag_router

app = FastAPI(title="Jarvis API", version="0.1.0")

# -----------------------------------------------------------------------------
# Production-safe HTTP adapter (small + compatible)
# - request_id / trace_id for observability
# - validation errors return 400 (instead of FastAPI default 422)
# - adds /v1/health required by tests/contract (keeps legacy /health too)
# -----------------------------------------------------------------------------

class _IdsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        tid = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
        request.state.request_id = rid
        request.state.trace_id = tid
        resp = await call_next(request)
        resp.headers["X-Request-Id"] = rid
        resp.headers["X-Trace-Id"] = tid
        return resp

app.add_middleware(_IdsMiddleware)

def _err(request: Request, status: int, code: str, message: str, details=None):
    return JSONResponse(
        status_code=status,
        content={
            "error_code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )

@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    return _err(request, 400, "bad_request", "Invalid payload", details=exc.errors())

# Routers (unchanged business logic)
app.include_router(chat_router)
app.include_router(state_router)
app.include_router(plan_router)
app.include_router(diag_router)

@app.get("/v1/health")
def v1_health(request: Request):
    return {
        "ok": True,
        "version": app.version,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(request.state, "request_id", None),
        "trace_id": getattr(request.state, "trace_id", None),
    }

@app.get("/health")
def health():
    return {"ok": True}

# -----------------------------------------------------------------------------
# Reminder scheduler startup (kept), but can be disabled for tests/CI
# -----------------------------------------------------------------------------
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

from app.db import SessionLocal
from app.models import Reminder

try:
    from app.db import init_db  # type: ignore
except Exception:  # pragma: no cover
    init_db = None  # type: ignore

scheduler = BackgroundScheduler(timezone=ZoneInfo("Europe/Warsaw"))

def _tick_reminders():
    db = SessionLocal()
    try:
        now = datetime.now(tz=ZoneInfo("Europe/Warsaw")).replace(tzinfo=None)
        due = db.query(Reminder).filter(Reminder.sent == False, Reminder.remind_at <= now).all()
        for r in due:
            print(f"[REMINDER] {r.message} @ {r.remind_at}")
            r.sent = True
            r.sent_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

@app.on_event("startup")
def _startup():
    if init_db:
        init_db()

    disable = os.getenv("JARVIS_DISABLE_SCHEDULER", "").strip() in {"1", "true", "True", "yes", "YES"} or bool(os.getenv("PYTEST_CURRENT_TEST"))
    if disable:
        return

    scheduler.add_job(_tick_reminders, "interval", seconds=30)
    scheduler.start()
