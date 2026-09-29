from copy import deepcopy
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_capabilities import MODEL_CAPABILITIES
from app.models import BillingPolicy, CreditPolicy, ModelAdminSetting


class ModelDisabledError(ValueError):
    error_key = "model_disabled"


def policy_data(policy: BillingPolicy) -> dict[str, Any]:
    return {
        "version": policy.version,
        "recharge_min_cents": policy.recharge_min_cents,
        "recharge_max_cents": policy.recharge_max_cents,
        "unit_amount_cents": policy.unit_amount_cents,
        "unit_credits": policy.unit_credits,
        "idr_recharge_min": policy.idr_recharge_min,
        "idr_recharge_max": policy.idr_recharge_max,
        "idr_unit_amount": policy.idr_unit_amount,
        "idr_unit_credits": policy.idr_unit_credits,
    }


def policy_snapshot(policy: BillingPolicy) -> dict[str, Any]:
    value = Decimal(policy.unit_amount_cents) / Decimal(100 * policy.unit_credits)
    return {**policy_data(policy), "credit_value_yuan": str(value)}


async def get_billing_policy(db: AsyncSession, *, lock: bool = False) -> BillingPolicy:
    statement = select(BillingPolicy).where(BillingPolicy.key == "default")
    if lock:
        statement = statement.with_for_update()
    policy = await db.scalar(statement)
    if not policy:
        raise RuntimeError("计费政策未初始化")
    return policy


def credit_policy_data(policy: CreditPolicy) -> dict[str, Any]:
    return {
        "version": policy.version,
        "registration_bonus_enabled": policy.registration_bonus_enabled,
        "registration_bonus_credits": policy.registration_bonus_credits,
        "daily_refill_enabled": policy.daily_refill_enabled,
        "daily_minimum_credits": policy.daily_minimum_credits,
    }


async def get_credit_policy(db: AsyncSession, *, lock: bool = False) -> CreditPolicy:
    statement = select(CreditPolicy).where(CreditPolicy.key == "default")
    if lock:
        statement = statement.with_for_update()
    policy = await db.scalar(statement)
    if not policy:
        raise RuntimeError("积分策略未初始化")
    return policy


async def get_model_settings(db: AsyncSession) -> list[ModelAdminSetting]:
    return list(
        await db.scalars(
            select(ModelAdminSetting).order_by(
                ModelAdminSetting.media_type, ModelAdminSetting.model_id
            )
        )
    )


async def get_model_setting(
    db: AsyncSession, media_type: str, model_id: str, *, lock: bool = False
) -> ModelAdminSetting | None:
    statement = select(ModelAdminSetting).where(
        ModelAdminSetting.media_type == media_type,
        ModelAdminSetting.model_id == model_id,
    )
    if lock:
        statement = statement.with_for_update()
    return await db.scalar(statement)


async def ensure_model_enabled(
    db: AsyncSession, media_type: str, model_id: str
) -> None:
    setting = await get_model_setting(db, media_type, model_id)
    if not setting or not setting.enabled:
        raise ModelDisabledError(f"{model_id} 当前未启用")


def model_settings_payload(settings: list[ModelAdminSetting]) -> list[dict[str, Any]]:
    setting_index = {(item.media_type, item.model_id): item for item in settings}
    rows = []
    for media_type, capability in MODEL_CAPABILITIES.items():
        for model in capability["models"]:
            setting = setting_index.get((media_type, model["id"]))
            if not setting:
                continue
            rows.append(
                {
                    "media_type": media_type,
                    "model_id": model["id"],
                    "label": setting.label,
                    "enabled": setting.enabled,
                    "is_default": setting.is_default,
                }
            )
    return rows


def merged_capabilities(settings: list[ModelAdminSetting]) -> dict[str, Any]:
    setting_index = {(item.media_type, item.model_id): item for item in settings}
    payload: dict[str, Any] = {}
    for media_type, capability in MODEL_CAPABILITIES.items():
        models = []
        default_model = None
        for model in capability["models"]:
            setting = setting_index.get((media_type, model["id"]))
            if not setting or not setting.enabled:
                continue
            public_model = {
                key: deepcopy(value)
                for key, value in model.items()
                if not key.startswith("_")
            }
            public_model["label"] = setting.label
            models.append(public_model)
            if setting.is_default:
                default_model = setting.model_id
        if not models or not default_model:
            raise RuntimeError(f"{media_type} 模型配置无可用默认模型")
        payload[media_type] = {"default_model": default_model, "models": models}
    return payload
