import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, CreditLedger, ModelPriceRule, User


def user_snapshot(user: User) -> dict[str, Any]:
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "credit_balance": user.credit_balance,
        "credit_frozen": user.credit_frozen,
    }


def price_snapshot(rule: ModelPriceRule) -> dict[str, Any]:
    return {
        "provider": rule.provider,
        "media_type": rule.media_type,
        "model": rule.model,
        "specification": rule.specification,
        "billing_unit": rule.billing_unit,
        "cost_per_unit": str(rule.cost_per_unit) if rule.cost_per_unit is not None else None,
        "input_cost_per_million": str(rule.input_cost_per_million) if rule.input_cost_per_million is not None else None,
        "output_cost_per_million": str(rule.output_cost_per_million) if rule.output_cost_per_million is not None else None,
        "base_credits": rule.base_credits,
        "freeze_credits": rule.freeze_credits,
        "multiplier": str(rule.multiplier),
        "enabled": rule.enabled,
    }


def add_audit(
    db: AsyncSession,
    *,
    admin_id: uuid.UUID,
    action: str,
    target_type: str,
    target_id: uuid.UUID | str,
    reason: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    db.add(
        AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            reason=reason,
            before_snapshot=before,
            after_snapshot=after,
        )
    )


async def adjust_credits(
    db: AsyncSession,
    *,
    admin: User,
    user_id: uuid.UUID,
    amount: int,
    reason: str,
) -> User:
    user = await db.scalar(select(User).where(User.id == user_id, User.is_system.is_(False)).with_for_update())
    if not user:
        raise ValueError("用户不存在")
    if user.credit_balance + amount < 0:
        raise ValueError("扣减后可用积分不能小于 0")
    before = user_snapshot(user)
    user.credit_balance += amount
    db.add(
        CreditLedger(
            user_id=user.id,
            entry_type="adjustment",
            amount=amount,
            balance_after=user.credit_balance,
            frozen_after=user.credit_frozen,
            idempotency_key=f"admin:{admin.id}:adjustment:{uuid.uuid4().hex}",
            note=reason,
        )
    )
    add_audit(db, admin_id=admin.id, action="adjust_credits", target_type="user", target_id=user.id, reason=reason, before=before, after=user_snapshot(user))
    await db.commit()
    await db.refresh(user)
    return user


async def active_admin_count(db: AsyncSession) -> int:
    return int(await db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.status == "active", User.is_system.is_(False))) or 0)
