from datetime import date

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreditLedger, User
from app.services.admin_configuration import get_credit_policy


async def grant_registration_credits(db: AsyncSession, user: User) -> int:
    policy = await get_credit_policy(db)
    if not policy.registration_bonus_enabled:
        return 0
    amount = policy.registration_bonus_credits
    user.credit_balance += amount
    db.add(
        CreditLedger(
            user_id=user.id,
            entry_type="system",
            amount=amount,
            balance_after=user.credit_balance,
            frozen_after=user.credit_frozen,
            idempotency_key=f"registration-bonus:{user.id}",
            note="新用户注册赠送",
        )
    )
    return amount


async def apply_daily_credit_floor(db: AsyncSession, grant_date: date) -> tuple[int, int]:
    policy = await get_credit_policy(db)
    if not policy.daily_refill_enabled:
        return 0, 0
    key_prefix = f"daily-floor:{grant_date.isoformat()}:"
    already_granted = exists(
        select(CreditLedger.id).where(
            CreditLedger.user_id == User.id,
            CreditLedger.idempotency_key.like(f"{key_prefix}%"),
        )
    )
    users = list(
        await db.scalars(
            select(User)
            .where(
                User.is_system.is_(False),
                User.status == "active",
                User.credit_balance < policy.daily_minimum_credits,
                ~already_granted,
            )
            .with_for_update()
        )
    )
    total = 0
    for user in users:
        amount = policy.daily_minimum_credits - user.credit_balance
        user.credit_balance = policy.daily_minimum_credits
        total += amount
        db.add(
            CreditLedger(
                user_id=user.id,
                entry_type="system",
                amount=amount,
                balance_after=user.credit_balance,
                frozen_after=user.credit_frozen,
                idempotency_key=f"{key_prefix}{user.id}",
                note="每日免费积分补足",
            )
        )
    return len(users), total
