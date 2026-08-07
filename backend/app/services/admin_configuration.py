from copy import deepcopy
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_capabilities import MODEL_CAPABILITIES
from app.models import BillingPolicy, ContentTemplate, ModelAdminSetting


TEMPLATE_KEYS = {"product_visual", "product_storyboard"}
PRODUCT_VISUAL_GROUPS = {
    "basic": ("white-bg", "first-screen", "multi-angle", "series-show"),
    "marketing": ("core-selling", "use-scenario", "ambient-scene", "contrast-effect"),
    "detail": ("detail-zoom", "specs-info", "tech-specs", "manufacturing", "ingredients"),
    "trust": ("brand-story", "freebies", "warranty", "usage-tips"),
}
STORYBOARD_TEMPLATE_ID = "ugc-seeding"
STORYBOARD_DURATIONS = {15, 30, 45, 60}


class ModelDisabledError(ValueError):
    pass


def policy_data(policy: BillingPolicy) -> dict[str, Any]:
    return {
        "version": policy.version,
        "recharge_min_cents": policy.recharge_min_cents,
        "recharge_max_cents": policy.recharge_max_cents,
        "unit_amount_cents": policy.unit_amount_cents,
        "unit_credits": policy.unit_credits,
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


def template_data(template: ContentTemplate) -> dict[str, Any]:
    return {
        "key": template.key,
        "version": template.version,
        "enabled": template.enabled,
        "config": deepcopy(template.config),
    }


async def get_product_templates(db: AsyncSession) -> dict[str, dict[str, Any]]:
    templates = list(
        await db.scalars(
            select(ContentTemplate).where(ContentTemplate.key.in_(TEMPLATE_KEYS))
        )
    )
    result = {template.key: template_data(template) for template in templates}
    if set(result) != TEMPLATE_KEYS:
        raise RuntimeError("商品模板未初始化")
    return result


def _text(value: Any, label: str, *, max_length: int = 6000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        raise ValueError(f"{label}无效")
    return value.strip()


def validate_template_config(key: str, value: Any) -> dict[str, Any]:
    if key not in TEMPLATE_KEYS or not isinstance(value, dict):
        raise ValueError("模板配置无效")
    if key == "product_visual":
        groups = value.get("groups")
        if not isinstance(groups, list) or len(groups) != len(PRODUCT_VISUAL_GROUPS):
            raise ValueError("商品图种分组无效")
        result_groups = []
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError("商品图种分组无效")
            group_id = group.get("id")
            expected_ids = PRODUCT_VISUAL_GROUPS.get(group_id)
            items = group.get("items")
            if not expected_ids or not isinstance(items, list) or [item.get("id") if isinstance(item, dict) else None for item in items] != list(expected_ids):
                raise ValueError("图种 ID 不允许修改或删除")
            result_groups.append(
                {
                    "id": group_id,
                    "label": _text(group.get("label"), "图种分组名称", max_length=64),
                    "items": [
                        {
                            "id": item["id"],
                            "label": _text(item.get("label"), "图种名称", max_length=64),
                            "default_enabled": bool(item.get("default_enabled")),
                        }
                        for item in items
                    ],
                }
            )
        if not any(item["default_enabled"] for group in result_groups for item in group["items"]):
            raise ValueError("至少保留一个默认图种")
        instruction = value.get("business_instruction", "")
        if not isinstance(instruction, str) or len(instruction.strip()) > 6000:
            raise ValueError("商品图种业务指令无效")
        return {"groups": result_groups, "business_instruction": instruction.strip()}

    templates = value.get("templates")
    durations = value.get("durations")
    if not isinstance(templates, list) or len(templates) != 1 or not isinstance(templates[0], dict):
        raise ValueError("商品分镜模板无效")
    template = templates[0]
    if template.get("id") != STORYBOARD_TEMPLATE_ID:
        raise ValueError("分镜模板 ID 不允许修改")
    if not isinstance(durations, list) or not durations or any(item not in STORYBOARD_DURATIONS for item in durations):
        raise ValueError("商品分镜时长无效")
    instruction = _text(value.get("business_instruction"), "商品分镜业务指令")
    return {
        "templates": [
            {
                "id": STORYBOARD_TEMPLATE_ID,
                "label": _text(template.get("label"), "分镜模板名称", max_length=64),
                "description": _text(template.get("description"), "分镜模板描述", max_length=255),
                "enabled": bool(template.get("enabled")),
            }
        ],
        "durations": sorted(set(durations)),
        "business_instruction": instruction,
    }
