from sqlalchemy import String, DateTime, Text, Integer, Float, JSON, ForeignKey, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import Any
from .db import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    actor: Mapped[str] = mapped_column(String(120), default="unknown", nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)  # pending/approved/rejected
    actor: Mapped[str] = mapped_column(String(120), default="unknown", nullable=False)
    action_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

# --- Compatibility shim ---
# Some parts of the codebase import Actor from app.models.
# The canonical definition lives in app.security.entra_jwt.
try:
    from app.security.entra_jwt import Actor  # type: ignore
except Exception:  # pragma: no cover
    from dataclasses import dataclass
    from typing import List

    @dataclass
    class Actor:  # fallback
        user_id: str
        roles: List[str]
class UserFact(Base):
    __tablename__ = "user_facts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)

    source: Mapped[str] = mapped_column(String(40), default="user_explicit", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class DayPlan(Base):
    __tablename__ = "day_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    day: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="b2c", nullable=False)  # b2c/pro
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    items = relationship("PlanItem", cascade="all, delete-orphan", passive_deletes=True)


class PlanItem(Base):
    __tablename__ = "plan_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day_plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("day_plans.id", ondelete="CASCADE"), index=True, nullable=False)

    type: Mapped[str] = mapped_column(String(30), default="chore", nullable=False)  # appointment/chore/shopping
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reminders = relationship("Reminder", cascade="all, delete-orphan", passive_deletes=True)


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("plan_items.id", ondelete="CASCADE"), index=True, nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class UserDayState(Base):
    __tablename__ = "user_day_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(20), default="day", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

