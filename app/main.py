from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.api.state import router as state_router
from app.api.plan import router as plan_router
from app.api.diag import router as diag_router

app = FastAPI(title="Jarvis API", version="0.1.0")
app.include_router(chat_router)
app.include_router(state_router)
app.include_router(plan_router)
app.include_router(diag_router)

from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

from app.db import SessionLocal
from app.models import Reminder

try:
    # optional: if you have init_db() in app.db (older patches), we will call it
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
    scheduler.add_job(_tick_reminders, "interval", seconds=30)
    scheduler.start()

@app.get("/health")
def health():
    return {"ok": True}
