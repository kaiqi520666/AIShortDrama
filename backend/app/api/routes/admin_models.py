from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, RequestError
from app.core.identity import get_current_admin
from app.core.model_capabilities import get_model_capability
from app.core.database import get_db
from app.models import ModelAdminSetting, User
from app.schemas.admin import ModelAdminSettingUpdateRequest
from app.schemas.response import success
from app.services.admin import add_audit
from app.services.admin_configuration import model_settings_payload

router = APIRouter()


@router.get("/models")
async def list_admin_models(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    from app.services.admin_configuration import get_model_settings

    return success(model_settings_payload(await get_model_settings(db)))


@router.put("/models/{media_type}/{model_id}")
async def update_admin_model(
    media_type: str,
    model_id: str,
    payload: ModelAdminSettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        get_model_capability(media_type, model_id)
    except ValueError as exc:
        raise NotFoundError("模型不存在") from exc
    settings = list(
        await db.scalars(
            select(ModelAdminSetting)
            .where(ModelAdminSetting.media_type == media_type)
            .with_for_update()
        )
    )
    setting = next((item for item in settings if item.model_id == model_id), None)
    if not setting:
        raise NotFoundError("模型设置不存在")
    before = {"label": setting.label, "enabled": setting.enabled, "is_default": setting.is_default}
    if setting.is_default and not payload.is_default:
        raise RequestError("请先设置其他启用模型为默认模型")
    if setting.is_default and not payload.enabled:
        raise RequestError("请先设置其他启用模型为默认模型")
    if payload.is_default and not payload.enabled:
        raise RequestError("默认模型必须启用")
    setting.label = payload.label
    setting.enabled = payload.enabled
    if payload.is_default:
        for item in settings:
            item.is_default = item.id == setting.id
    if not any(item.enabled and item.is_default for item in settings):
        raise RequestError("每种媒体必须保留一个启用的默认模型")
    after = {"label": setting.label, "enabled": setting.enabled, "is_default": setting.is_default}
    add_audit(
        db,
        admin_id=admin.id,
        action="update_model_setting",
        target_type="model_admin_setting",
        target_id=setting.id,
        reason=payload.reason,
        before=before,
        after=after,
    )
    await db.commit()
    return success(next(item for item in model_settings_payload(settings) if item["model_id"] == model_id))
