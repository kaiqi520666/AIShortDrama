import uuid
from datetime import UTC, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import CreditLedger, GenerationTask, User
from app.schemas.response import success

router = APIRouter()
BEIJING = timezone(timedelta(hours=8))
LEDGER_TYPES = {
    "consume": "consume",
    "refund": "refund",
    "adjustment": "system",
    "recharge": "recharge",
}


@router.get("")
async def get_account(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    user = await db.get(User, user_id)
    today = datetime.combine(datetime.now(BEIJING).date(), time.min, BEIJING).astimezone(UTC)
    consumed_total, consumed_today = (
        await db.execute(
            select(
                func.coalesce(func.sum(CreditLedger.amount), 0),
                func.coalesce(
                    func.sum(CreditLedger.amount).filter(CreditLedger.created_at >= today),
                    0,
                ),
            ).where(
                CreditLedger.user_id == user_id,
                CreditLedger.entry_type == "consume",
            )
        )
    ).one()
    return success(
        {
            "user": {
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            },
            "credits": {
                "available": user.credit_balance,
                "frozen": user.credit_frozen,
                "consumed_total": int(consumed_total),
                "consumed_today": int(consumed_today),
            },
        }
    )


@router.get("/credits")
async def list_credit_ledger(
    entry_type: Literal["all", "recharge", "consume", "refund", "system"] = Query(
        "all", alias="type"
    ),
    media_type: Literal["all", "text", "image", "video", "audio"] = "all",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    conditions = [
        CreditLedger.user_id == user_id,
        CreditLedger.entry_type.in_(LEDGER_TYPES),
    ]
    if entry_type != "all":
        stored_type = "adjustment" if entry_type == "system" else entry_type
        conditions.append(CreditLedger.entry_type == stored_type)
    if media_type != "all":
        conditions.append(
            GenerationTask.pricing_snapshot["media_type"].as_string() == media_type
        )
    if start_at:
        conditions.append(CreditLedger.created_at >= start_at)
    if end_at:
        conditions.append(CreditLedger.created_at < end_at)

    join_on = GenerationTask.id == CreditLedger.task_id
    total = await db.scalar(
        select(func.count())
        .select_from(CreditLedger)
        .outerjoin(GenerationTask, join_on)
        .where(*conditions)
    )
    rows = (
        await db.execute(
            select(CreditLedger, GenerationTask)
            .outerjoin(GenerationTask, join_on)
            .where(*conditions)
            .order_by(CreditLedger.created_at.desc(), CreditLedger.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = []
    for entry, task in rows:
        public_type = LEDGER_TYPES[entry.entry_type]
        delta = -abs(entry.amount) if public_type == "consume" else entry.amount
        media = task.pricing_snapshot.get("media_type") if task else None
        items.append(
            {
                "id": str(entry.id),
                "type": public_type,
                "delta": delta,
                "balance_after": entry.balance_after,
                "media_type": media,
                "model": task.model if task else None,
                "note": entry.note,
                "created_at": entry.created_at.isoformat(),
            }
        )
    return success(
        {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total or 0,
        }
    )
