from __future__ import annotations

from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DayPlan, PlanItem, Reminder
from app.schemas import PlanItemCreate, DayPlanOut, PlanItemOut


router = APIRouter(prefix="/v1", tags=["plan"])


def get_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    return (x_user_id or "local").strip()


def _get_or_create_day_plan(db: Session, user_id: str, day: date, mode: str) -> DayPlan:
    dp = db.query(DayPlan).filter(DayPlan.user_id == user_id, DayPlan.day == day).first()
    if dp:
        return dp
    dp = DayPlan(user_id=user_id, day=day, mode=mode)
    db.add(dp)
    db.commit()
    db.refresh(dp)
    return dp


@router.post("/plan/items", response_model=PlanItemOut)
def add_plan_item(payload: PlanItemCreate, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    dp = _get_or_create_day_plan(db, user_id, payload.day, payload.mode or "b2c")

    item = PlanItem(
        day_plan_id=dp.id,
        type=payload.type,
        title=payload.title,
        start_time=payload.start_time,
        location=payload.location,
        priority=payload.priority,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # MVP reminder: if start_time exists -> reminder 40 minutes earlier
    if item.start_time:
        remind_at = item.start_time - timedelta(minutes=40)
        msg = f"Przypomnienie: {item.title}"
        if item.start_time:
            msg += f" ({item.start_time.strftime('%H:%M')})"
        db.add(Reminder(plan_item_id=item.id, remind_at=remind_at, message=msg))
        db.commit()

    return PlanItemOut(
        id=item.id,
        type=item.type,
        title=item.title,
        start_time=item.start_time,
        location=item.location,
        priority=item.priority,
        notes=item.notes,
    )


@router.get("/plan/today", response_model=DayPlanOut)
def get_today(db: Session = Depends(get_db), user_id: str = Depends(get_user_id)):
    today = date.today()
    dp = db.query(DayPlan).filter(DayPlan.user_id == user_id, DayPlan.day == today).first()
    if not dp:
        return DayPlanOut(day=today, summary=None, items=[])

    items = (
        db.query(PlanItem)
        .filter(PlanItem.day_plan_id == dp.id)
        .order_by(PlanItem.priority.desc(), PlanItem.start_time.is_(None), PlanItem.start_time.asc())
        .all()
    )

    return DayPlanOut(
        day=today,
        summary=dp.summary,
        items=[
            PlanItemOut(
                id=i.id,
                type=i.type,
                title=i.title,
                start_time=i.start_time,
                location=i.location,
                priority=i.priority,
                notes=i.notes,
            )
            for i in items
        ],
    )
