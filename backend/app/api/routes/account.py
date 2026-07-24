import uuid
from datetime import UTC, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import CreditLedger, User
from app.schemas.response import success

router = APIRouter()
BEIJING = timezone(timedelta(hours=8))


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
