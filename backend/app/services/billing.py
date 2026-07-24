from decimal import Decimal, ROUND_CEILING
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreditLedger, GenerationTask, ModelPriceRule, User


CREDIT_VALUE_YUAN = Decimal("0.035")
DEFAULT_IMAGE_RESOLUTIONS = {
    "gpt-image-2": "1K",
    "doubao-seedream-5-0-pro": "2K",
    "doubao-seedream-5-0": "2K",
    "gemini-3-pro-image-preview": "1K",
    "gemini-3.1-flash-image-preview": "1K",
}


class BillingError(RuntimeError):
    pass


class InsufficientCredits(BillingError):
    pass


def _ceil(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_CEILING))


def _unit_credits(rule: ModelPriceRule) -> int:
    multiplier = Decimal(rule.multiplier)
    if rule.base_credits is not None:
        return _ceil(Decimal(rule.base_credits) * multiplier)
    if rule.cost_per_unit is None:
        raise BillingError("模型价格配置不完整")
    return _ceil(Decimal(rule.cost_per_unit) * multiplier / CREDIT_VALUE_YUAN)


async def get_price_rule(
    db: AsyncSession,
    media_type: str,
    model: str,
    specification: str = "",
) -> ModelPriceRule:
    rule = await db.scalar(
        select(ModelPriceRule).where(
            ModelPriceRule.media_type == media_type,
            ModelPriceRule.model == model,
            ModelPriceRule.specification == specification,
            ModelPriceRule.enabled.is_(True),
        )
    )
    if not rule:
        raise BillingError("当前模型价格未配置")
    return rule


async def build_price_snapshot(
    db: AsyncSession,
    media_type: str,
    model: str,
    *,
    resolution: str | None = None,
    duration: int | None = None,
) -> dict[str, Any]:
    specification = (
        resolution or DEFAULT_IMAGE_RESOLUTIONS.get(model, "")
        if media_type == "image"
        else ""
    )
    rule = await get_price_rule(db, media_type, model, specification or "")
    unit_credits = _unit_credits(rule)
    if media_type == "video":
        if not duration or duration <= 0:
            raise BillingError("视频时长无效")
        frozen_credits = unit_credits * duration
        quantity = duration
    elif media_type == "audio":
        frozen_credits = _ceil(Decimal(rule.freeze_credits or 60) * rule.multiplier)
        quantity = 120
    else:
        frozen_credits = unit_credits
        quantity = 1
    return {
        "rule_id": str(rule.id),
        "provider": rule.provider,
        "media_type": media_type,
        "model": model,
        "specification": rule.specification,
        "billing_unit": rule.billing_unit,
        "cost_per_unit": str(rule.cost_per_unit) if rule.cost_per_unit is not None else None,
        "input_cost_per_million": str(rule.input_cost_per_million)
        if rule.input_cost_per_million is not None
        else None,
        "output_cost_per_million": str(rule.output_cost_per_million)
        if rule.output_cost_per_million is not None
        else None,
        "multiplier": str(rule.multiplier),
        "unit_credits": unit_credits,
        "quantity": quantity,
        "frozen_credits": frozen_credits,
    }


async def freeze_task_credits(
    db: AsyncSession,
    task: GenerationTask,
    media_type: str,
    *,
    resolution: str | None = None,
    duration: int | None = None,
) -> None:
    snapshot = await build_price_snapshot(
        db,
        media_type,
        task.model,
        resolution=resolution,
        duration=duration,
    )
    amount = snapshot["frozen_credits"]
    user = await db.scalar(select(User).where(User.id == task.user_id).with_for_update())
    if not user or user.credit_balance < amount:
        raise InsufficientCredits(f"积分不足，本次需要 {amount} 积分")
    user.credit_balance -= amount
    user.credit_frozen += amount
    task.pricing_snapshot = snapshot
    task.frozen_credits = amount
    task.credit_status = "frozen"
    db.add(
        CreditLedger(
            user_id=user.id,
            task_id=task.id,
            entry_type="freeze",
            amount=amount,
            balance_after=user.credit_balance,
            frozen_after=user.credit_frozen,
            idempotency_key=f"task:{task.id}:freeze",
            note=f"冻结 {task.model} 生成积分",
        )
    )


def _audio_charge(task: GenerationTask, original_duration: float) -> int:
    snapshot = task.pricing_snapshot
    cost = Decimal(snapshot["cost_per_unit"])
    multiplier = Decimal(snapshot["multiplier"])
    duration = Decimal(str(original_duration))
    return max(1, _ceil(duration / Decimal(60) * cost * multiplier / CREDIT_VALUE_YUAN))


async def settle_task_credits(
    db: AsyncSession,
    task: GenerationTask,
    *,
    original_duration: float | None = None,
) -> None:
    task = await db.scalar(
        select(GenerationTask).where(GenerationTask.id == task.id).with_for_update()
    )
    if not task:
        raise BillingError("生成任务不存在")
    if task.credit_status != "frozen":
        return
    user = await db.scalar(select(User).where(User.id == task.user_id).with_for_update())
    if not user:
        raise BillingError("积分账户不存在")
    charged = (
        min(task.frozen_credits, _audio_charge(task, original_duration))
        if task.pricing_snapshot.get("media_type") == "audio" and original_duration is not None
        else task.frozen_credits
    )
    user.credit_frozen -= charged
    task.charged_credits = charged
    db.add(
        CreditLedger(
            user_id=user.id,
            task_id=task.id,
            entry_type="consume",
            amount=charged,
            balance_after=user.credit_balance,
            frozen_after=user.credit_frozen,
            idempotency_key=f"task:{task.id}:consume",
            note=f"结算 {task.model} 生成积分",
        )
    )
    refund = task.frozen_credits - charged
    if refund:
        user.credit_frozen -= refund
        user.credit_balance += refund
        db.add(
            CreditLedger(
                user_id=user.id,
                task_id=task.id,
                entry_type="refund",
                amount=refund,
                balance_after=user.credit_balance,
                frozen_after=user.credit_frozen,
                idempotency_key=f"task:{task.id}:refund-difference",
                note="退还未使用的冻结积分",
            )
        )
    task.credit_status = "consumed"


async def refund_task_credits(db: AsyncSession, task: GenerationTask, note: str) -> None:
    task = await db.scalar(
        select(GenerationTask).where(GenerationTask.id == task.id).with_for_update()
    )
    if not task:
        raise BillingError("生成任务不存在")
    if task.credit_status != "frozen":
        return
    user = await db.scalar(select(User).where(User.id == task.user_id).with_for_update())
    if not user:
        raise BillingError("积分账户不存在")
    user.credit_frozen -= task.frozen_credits
    user.credit_balance += task.frozen_credits
    task.credit_status = "refunded"
    db.add(
        CreditLedger(
            user_id=user.id,
            task_id=task.id,
            entry_type="refund",
            amount=task.frozen_credits,
            balance_after=user.credit_balance,
            frozen_after=user.credit_frozen,
            idempotency_key=f"task:{task.id}:refund",
            note=note[:255],
        )
    )


def price_rule_payload(rule: ModelPriceRule) -> dict[str, Any]:
    unit_credits = _unit_credits(rule)
    return {
        "media_type": rule.media_type,
        "model": rule.model,
        "specification": rule.specification,
        "billing_unit": rule.billing_unit,
        "multiplier": str(rule.multiplier),
        "unit_credits": unit_credits,
        "freeze_credits": _ceil(Decimal(rule.freeze_credits) * rule.multiplier)
        if rule.freeze_credits is not None
        else unit_credits,
    }
