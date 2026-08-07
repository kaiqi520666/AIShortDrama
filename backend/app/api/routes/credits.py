import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import ModelPriceRule, User
from app.schemas.response import success
from app.services.billing import price_rule_payload
from app.services.admin_configuration import get_billing_policy, policy_snapshot

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
    policy = await get_billing_policy(db)
    credit_value_yuan = Decimal(policy_snapshot(policy)["credit_value_yuan"])
    return success(
        {
            "balance": user.credit_balance,
            "frozen": user.credit_frozen,
            "prices": [price_rule_payload(rule, credit_value_yuan) for rule in rules],
        }
    )
