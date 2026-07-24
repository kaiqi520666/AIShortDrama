import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import ModelPriceRule, User
from app.schemas.response import success
from app.services.billing import price_rule_payload

router = APIRouter()


@router.get("")
async def get_credits(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    user = await db.get(User, user_id)
    rules = await db.scalars(
        select(ModelPriceRule)
        .where(ModelPriceRule.enabled.is_(True))
        .order_by(ModelPriceRule.media_type, ModelPriceRule.model, ModelPriceRule.specification)
    )
    return success(
        {
            "balance": user.credit_balance,
            "frozen": user.credit_frozen,
            "prices": [price_rule_payload(rule) for rule in rules],
        }
    )
