import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, RequestError, ServiceUnavailableError, public_error_message
from app.core.identity import get_current_admin
from app.models import Character, Garment, OutfitModel, Scene, User
from app.providers.toapis import ToApisProvider
from app.schemas.admin import SystemReferenceAssetUpdateRequest
from app.schemas.response import success
from app.services.admin import add_audit
from app.services.media_upload import MediaUploadService, StoredMedia
from app.services.private_avatar import PrivateAvatarService


router = APIRouter()
logger = logging.getLogger(__name__)

RESOURCE_TYPES = {
    "model": (OutfitModel, "model_metadata", "outfit-models"),
    "character": (Character, "character_metadata", "characters"),
    "garment": (Garment, "garment_metadata", "garments"),
    "scene": (Scene, "scene_metadata", "scenes"),
}


def get_media_upload_service() -> MediaUploadService:
    return MediaUploadService()


def get_private_avatar_service() -> PrivateAvatarService:
    return PrivateAvatarService(provider_factory=ToApisProvider)


def _resource_config(resource_type: str):
    config = RESOURCE_TYPES.get(resource_type)
    if not config:
        raise NotFoundError("素材类型不存在")
    return config


def _metadata(item: Any, field: str) -> dict[str, Any]:
    value = getattr(item, field) or {}
    return dict(value) if isinstance(value, dict) else {}


def _library_data(metadata: dict[str, Any]) -> dict[str, Any]:
    library = metadata.get("library") or {}
    return {
        "tags": list(library.get("tags") or []),
        "copyright_note": str(library.get("copyright_note") or ""),
    }


def admin_asset_data(item: Any, resource_type: str) -> dict[str, Any]:
    _model, metadata_field, _folder = _resource_config(resource_type)
    metadata = _metadata(item, metadata_field)
    return {
        "id": str(item.id),
        "resource_type": resource_type,
        "name": item.name,
        "url": item.image_url,
        "width": item.width,
        "height": item.height,
        "active": item.active,
        "sort_order": item.sort_order,
        "library": _library_data(metadata),
        "seedance": metadata.get("seedance") if resource_type == "character" else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


async def _delete_stored_media(service: MediaUploadService, stored: StoredMedia) -> None:
    try:
        await service.delete(stored)
    except Exception:
        logger.exception("Failed to delete orphan system reference media", extra={"object_key": stored.object_key})


@router.get("/reference-assets")
async def list_system_reference_assets(
    resource_type: str = "all",
    active: str = "all",
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    resource_types = RESOURCE_TYPES if resource_type == "all" else {resource_type: _resource_config(resource_type)}
    if active not in {"all", "active", "inactive"}:
        raise RequestError("素材状态无效")
    items = []
    for key, (model, _field, _folder) in resource_types.items():
        statement = select(model).where(model.user_id.is_(None))
        if active != "all":
            statement = statement.where(model.active.is_(active == "active"))
        rows = list(await db.scalars(statement.order_by(model.sort_order, model.created_at)))
        items.extend(admin_asset_data(item, key) for item in rows)
    return success(items)


@router.post("/reference-assets")
async def create_system_reference_asset(
    resource_type: str = Form(...),
    file: UploadFile = File(...),
    name: str = Form(...),
    sort_order: int = Form(0),
    tags: str = Form(""),
    copyright_note: str = Form(""),
    reason: str = Form(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    model, metadata_field, folder = _resource_config(resource_type)
    if sort_order < 0 or sort_order > 100_000:
        raise RequestError("排序值无效")
    normalized_name = name.strip()
    normalized_reason = reason.strip()
    if not normalized_name or not normalized_reason:
        raise RequestError("素材名称和操作原因不能为空")
    tag_values = []
    for tag in tags.split(","):
        tag = tag.strip()
        if tag and len(tag) <= 32 and tag not in tag_values:
            tag_values.append(tag)
    if len(tag_values) > 20 or len(copyright_note.strip()) > 500:
        raise RequestError("素材标签或版权备注无效")
    service = get_media_upload_service()
    try:
        stored = await service.store(file, "image", f"library/system/{folder}")
    except ValueError as exc:
        raise RequestError(str(exc)) from exc
    except Exception as exc:
        logger.exception("System reference asset upload failed")
        raise ServiceUnavailableError(public_error_message(exc, "上传服务暂时不可用")) from exc
    metadata: dict[str, Any] = {
        "library": {"tags": tag_values, "copyright_note": copyright_note.strip()}
    }
    if resource_type == "character":
        try:
            metadata["seedance"] = await get_private_avatar_service().register(normalized_name, stored.url)
        except Exception as exc:
            message = public_error_message(exc, "虚拟人像服务暂时不可用")
            logger.exception("System character registration failed")
            metadata["seedance"] = {"provider": "toapis", "type": "private-avatar", "status": "failed", "error": message}
    item = model(
        user_id=None,
        name=normalized_name[:100],
        image_url=stored.url,
        object_key=stored.object_key,
        width=stored.width,
        height=stored.height,
        active=True,
        sort_order=sort_order,
        **{metadata_field: metadata},
    )
    db.add(item)
    try:
        await db.flush()
        add_audit(
            db,
            admin_id=admin.id,
            action="create_system_reference_asset",
            target_type=resource_type,
            target_id=item.id,
            reason=normalized_reason,
            before={},
            after=admin_asset_data(item, resource_type),
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        await _delete_stored_media(service, stored)
        raise ServiceUnavailableError("系统素材保存服务暂时不可用") from exc
    await db.refresh(item)
    return success(admin_asset_data(item, resource_type))


@router.put("/reference-assets/{resource_type}/{asset_id}")
async def update_system_reference_asset(
    resource_type: str,
    asset_id: uuid.UUID,
    payload: SystemReferenceAssetUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    model, metadata_field, _folder = _resource_config(resource_type)
    item = await db.scalar(
        select(model).where(model.id == asset_id, model.user_id.is_(None)).with_for_update()
    )
    if not item:
        raise NotFoundError("系统素材不存在")
    before = admin_asset_data(item, resource_type)
    metadata = _metadata(item, metadata_field)
    metadata["library"] = {
        "tags": payload.tags,
        "copyright_note": payload.copyright_note.strip(),
    }
    item.name = payload.name
    item.sort_order = payload.sort_order
    item.active = payload.active
    setattr(item, metadata_field, metadata)
    add_audit(
        db,
        admin_id=admin.id,
        action="update_system_reference_asset",
        target_type=resource_type,
        target_id=item.id,
        reason=payload.reason,
        before=before,
        after=admin_asset_data(item, resource_type),
    )
    await db.commit()
    await db.refresh(item)
    return success(admin_asset_data(item, resource_type))


@router.post("/reference-assets/character/{asset_id}/register")
async def register_system_character(
    asset_id: uuid.UUID,
    reason: str = Form(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    item = await db.scalar(
        select(Character)
        .where(Character.id == asset_id, Character.user_id.is_(None))
        .with_for_update()
    )
    if not item:
        raise NotFoundError("系统角色不存在")
    if not reason.strip():
        raise RequestError("操作原因不能为空")
    before = admin_asset_data(item, "character")
    metadata = _metadata(item, "character_metadata")
    try:
        metadata["seedance"] = await get_private_avatar_service().register(item.name, item.image_url)
    except Exception as exc:
        message = public_error_message(exc, "虚拟人像服务暂时不可用")
        logger.exception("System character registration retry failed", extra={"character_id": str(item.id)})
        metadata["seedance"] = {**(metadata.get("seedance") or {}), "status": "failed", "error": message}
        item.character_metadata = metadata
        add_audit(
            db,
            admin_id=admin.id,
            action="register_system_character_failed",
            target_type="character",
            target_id=item.id,
            reason=reason.strip(),
            before=before,
            after=admin_asset_data(item, "character"),
        )
        await db.commit()
        raise ServiceUnavailableError(message) from exc
    item.character_metadata = metadata
    add_audit(
        db,
        admin_id=admin.id,
        action="register_system_character",
        target_type="character",
        target_id=item.id,
        reason=reason.strip(),
        before=before,
        after=admin_asset_data(item, "character"),
    )
    await db.commit()
    await db.refresh(item)
    return success(admin_asset_data(item, "character"))
