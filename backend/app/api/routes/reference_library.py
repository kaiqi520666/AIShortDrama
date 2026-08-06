import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, RequestError, ServiceUnavailableError, public_error_message
from app.core.identity import get_current_user_id
from app.models import Asset, Character, Garment, OutfitModel
from app.providers.toapis import ToApisProvider
from app.schemas.response import success
from app.services.media_upload import MEDIA_UPLOAD_RULES, MediaUploadService, StoredMedia
from app.services.private_avatar import PrivateAvatarService
from app.services.storage import IMAGE_MAX_BYTES, OssStorage

router = APIRouter()
logger = logging.getLogger(__name__)

IMAGE_TYPES = MEDIA_UPLOAD_RULES["image"]["content_types"]
MAX_IMAGE_SIZE = IMAGE_MAX_BYTES


def get_media_upload_service() -> MediaUploadService:
    return MediaUploadService(storage_factory=OssStorage)


def get_private_avatar_service() -> PrivateAvatarService:
    return PrivateAvatarService(provider_factory=ToApisProvider)


async def register_virtual_character(
    name: str, source_url: str, group_id: str | None = None
) -> dict[str, Any]:
    """Compatibility wrapper for callers that still use the route helper."""
    return await get_private_avatar_service().register(name, source_url, group_id)


async def refresh_virtual_character(item: Character) -> dict[str, Any]:
    seedance = (item.character_metadata or {}).get("seedance") or {}
    if seedance.get("status") != "processing" or not seedance.get("asset_id"):
        return seedance
    refreshed = await get_private_avatar_service().refresh(seedance)
    if refreshed != seedance:
        item.character_metadata = {
            **(item.character_metadata or {}),
            "seedance": refreshed,
        }
    return refreshed


def reference_payload(item: OutfitModel | Character | Garment, resource_type: str) -> dict[str, Any]:
    metadata = {
        "model": getattr(item, "model_metadata", {}),
        "character": getattr(item, "character_metadata", {}),
        "garment": getattr(item, "garment_metadata", {}),
    }[resource_type]
    return {
        "id": str(item.id),
        "resource_type": resource_type,
        "source": "system" if item.user_id is None else "user",
        "name": item.name,
        "url": item.image_url,
        "width": item.width,
        "height": item.height,
        "metadata": metadata or {},
    }


async def store_reference_image(
    file: UploadFile, folder: str, service: MediaUploadService | None = None
) -> StoredMedia:
    return await (service or get_media_upload_service()).store(
        file, "image", f"library/{folder}"
    )


async def _delete_stored_media(service: MediaUploadService, stored: StoredMedia) -> None:
    try:
        await service.delete(stored)
    except Exception:
        logger.exception("Failed to delete orphan reference media", extra={"object_key": stored.object_key})


async def _commit_reference_item(
    db: AsyncSession,
    item: OutfitModel | Character | Garment,
    stored: StoredMedia | None = None,
    service: MediaUploadService | None = None,
) -> None:
    db.add(item)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        if stored and service:
            await _delete_stored_media(service, stored)
        raise ServiceUnavailableError("素材保存服务暂时不可用") from exc
    await db.refresh(item)


async def create_character_item(
    *,
    name: str,
    image_url: str,
    object_key: str | None,
    width: int | None,
    height: int | None,
    user_id: uuid.UUID,
    db: AsyncSession,
    source_asset_id: uuid.UUID | None = None,
    existing_seedance: dict[str, Any] | None = None,
    stored: StoredMedia | None = None,
    upload_service: MediaUploadService | None = None,
) -> Character:
    seedance = existing_seedance or {}
    if seedance.get("status") not in {"active", "processing"}:
        try:
            seedance = await register_virtual_character(name, image_url)
        except Exception as exc:
            message = public_error_message(exc, "虚拟人像服务暂时不可用")
            logger.exception("Virtual character registration failed")
            seedance = {
                "provider": "toapis",
                "type": "private-avatar",
                "status": "failed",
                "error": message,
            }
    item = Character(
        user_id=user_id,
        name=name,
        image_url=image_url,
        object_key=object_key,
        width=width,
        height=height,
        character_metadata={
            **({"source_asset_id": str(source_asset_id)} if source_asset_id else {}),
            "seedance": seedance,
        },
    )
    await _commit_reference_item(db, item, stored, upload_service)
    return item


@router.get("/outfit-models")
async def list_outfit_models(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    items = await db.scalars(
        select(OutfitModel)
        .where(
            OutfitModel.active.is_(True),
            or_(OutfitModel.user_id.is_(None), OutfitModel.user_id == user_id),
        )
        .order_by(OutfitModel.user_id.is_not(None), OutfitModel.sort_order, OutfitModel.created_at)
    )
    return success([reference_payload(item, "model") for item in items])


@router.post("/outfit-models")
async def upload_outfit_model(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = get_media_upload_service()
    try:
        stored = await store_reference_image(file, "outfit-models", service)
    except ValueError as exc:
        raise RequestError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Outfit model upload failed")
        raise ServiceUnavailableError(public_error_message(exc, "上传服务暂时不可用")) from exc
    item = OutfitModel(
        user_id=user_id,
        name=((name or file.filename or "我的模特").rsplit(".", 1)[0].strip() or "我的模特")[:100],
        image_url=stored.url,
        object_key=stored.object_key,
        width=stored.width,
        height=stored.height,
    )
    await _commit_reference_item(db, item, stored, service)
    return success(reference_payload(item, "model"))


@router.get("/characters")
async def list_characters(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    items = list(await db.scalars(
        select(Character)
        .where(
            Character.active.is_(True),
            or_(Character.user_id.is_(None), Character.user_id == user_id),
        )
        .order_by(Character.user_id.is_not(None), Character.sort_order, Character.created_at)
    ))
    return success([reference_payload(item, "character") for item in items])


@router.post("/characters")
async def upload_character(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = get_media_upload_service()
    try:
        stored = await store_reference_image(file, "characters", service)
    except ValueError as exc:
        raise RequestError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Character upload failed")
        raise ServiceUnavailableError(public_error_message(exc, "上传服务暂时不可用")) from exc
    character_name = ((name or file.filename or "我的角色").rsplit(".", 1)[0].strip() or "我的角色")[:100]
    item = await create_character_item(
        name=character_name,
        image_url=stored.url,
        object_key=stored.object_key,
        width=stored.width,
        height=stored.height,
        user_id=user_id,
        db=db,
        stored=stored,
        upload_service=service,
    )
    return success(reference_payload(item, "character"))


@router.post("/characters/from-asset/{asset_id}")
async def create_character_from_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    asset = await db.scalar(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.user_id == user_id,
            Asset.deleted_at.is_(None),
        )
    )
    if not asset:
        raise NotFoundError("素材不存在")
    if asset.media_type != "image":
        raise RequestError("仅图片素材可注册为角色")
    name = ((asset.name or "我的角色").rsplit(".", 1)[0].strip() or "我的角色")[:100]
    item = await create_character_item(
        name=name,
        image_url=asset.url,
        object_key=asset.object_key,
        width=asset.width,
        height=asset.height,
        user_id=user_id,
        db=db,
        source_asset_id=asset.id,
        existing_seedance=(asset.asset_metadata or {}).get("seedance"),
    )
    return success(reference_payload(item, "character"))


@router.post("/characters/{character_id}/register")
async def register_character(
    character_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    item = await db.scalar(
        select(Character).where(
            Character.id == character_id,
            or_(Character.user_id.is_(None), Character.user_id == user_id),
        )
    )
    if not item:
        raise NotFoundError("角色不存在")
    try:
        seedance = (item.character_metadata or {}).get("seedance") or {}
        if seedance.get("status") == "processing" and seedance.get("asset_id"):
            await refresh_virtual_character(item)
        elif seedance.get("status") != "active":
            item.character_metadata = {
                **(item.character_metadata or {}),
                "seedance": await register_virtual_character(item.name, item.image_url),
            }
        await db.commit()
        await db.refresh(item)
        return success(reference_payload(item, "character"))
    except Exception as exc:
        message = public_error_message(exc, "虚拟人像服务暂时不可用")
        logger.exception("Character registration failed", extra={"character_id": str(item.id)})
        item.character_metadata = {
            **(item.character_metadata or {}),
            "seedance": {
                **((item.character_metadata or {}).get("seedance") or {}),
                "status": "failed",
                "error": message,
            },
        }
        await db.commit()
        raise ServiceUnavailableError(message, reference_payload(item, "character")) from exc


@router.get("/garments")
async def list_garments(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    items = await db.scalars(
        select(Garment)
        .where(
            Garment.active.is_(True),
            or_(Garment.user_id.is_(None), Garment.user_id == user_id),
        )
        .order_by(Garment.user_id.is_not(None), Garment.sort_order, Garment.created_at)
    )
    return success([reference_payload(item, "garment") for item in items])


@router.post("/garments")
async def upload_garment(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = get_media_upload_service()
    try:
        stored = await store_reference_image(file, "garments", service)
    except ValueError as exc:
        raise RequestError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Garment upload failed")
        raise ServiceUnavailableError(public_error_message(exc, "上传服务暂时不可用")) from exc
    item = Garment(
        user_id=user_id,
        name=((name or file.filename or "我的服饰").rsplit(".", 1)[0].strip() or "我的服饰")[:100],
        image_url=stored.url,
        object_key=stored.object_key,
        width=stored.width,
        height=stored.height,
    )
    await _commit_reference_item(db, item, stored, service)
    return success(reference_payload(item, "garment"))
