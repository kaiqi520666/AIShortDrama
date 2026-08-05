import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import Asset, Character, Garment, OutfitModel
from app.providers.toapis import ToApisError, ToApisProvider
from app.schemas.response import fail, success
from app.services.image_processing import normalize_image
from app.services.storage import OssStorage

router = APIRouter()

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024


def avatar_metadata(data: dict[str, Any]) -> dict[str, Any]:
    asset_id = data.get("asset_id")
    return {
        "provider": "toapis",
        "type": "private-avatar",
        "group_id": data.get("group_id"),
        "asset_id": asset_id,
        "asset_url": data.get("asset_url") or (f"asset://{asset_id}" if asset_id else None),
        "status": data.get("status") or "processing",
    }


async def register_virtual_character(name: str, source_url: str) -> dict[str, Any]:
    async with ToApisProvider() as provider:
        group = await provider.create_private_avatar_group(name)
        group_id = group.get("group_id")
        if not group_id:
            raise ToApisError("ToAPIs 未返回虚拟角色组 ID")
        asset = await provider.upload_private_avatar(group_id, source_url, name)
        asset["group_id"] = group_id
        if not asset.get("asset_id"):
            raise ToApisError("ToAPIs 未返回虚拟角色素材 ID")
        return avatar_metadata(asset)


async def refresh_virtual_character(item: Character) -> None:
    seedance = (item.character_metadata or {}).get("seedance") or {}
    if seedance.get("status") != "processing" or not seedance.get("asset_id"):
        return
    async with ToApisProvider() as provider:
        state = await provider.get_private_avatar(seedance["asset_id"])
    item.character_metadata = {
        **(item.character_metadata or {}),
        "seedance": {**seedance, **avatar_metadata({**state, "group_id": seedance.get("group_id")})},
    }


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


async def store_reference_image(file: UploadFile, folder: str) -> dict[str, Any]:
    if file.content_type not in IMAGE_TYPES:
        raise ValueError("仅支持 JPG、PNG、WebP 图片")
    if not file.size:
        raise ValueError("上传文件不能为空")
    if file.size > MAX_IMAGE_SIZE:
        raise ValueError("图片不能超过 20MB")
    try:
        await file.seek(0)
        normalized = await asyncio.to_thread(normalize_image, file.file, file.content_type)
        if normalized.size > MAX_IMAGE_SIZE:
            raise ValueError("重编码后的图片不能超过 20MB")
        date_path = datetime.now(UTC).strftime("%Y/%m/%d")
        object_key = f"library/{folder}/{date_path}/{uuid.uuid4().hex}{IMAGE_TYPES[file.content_type]}"
        url = await OssStorage().store_upload(object_key, normalized.stream, file.content_type)
        return {
            "url": url,
            "object_key": object_key,
            "width": normalized.width,
            "height": normalized.height,
        }
    finally:
        await file.close()


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
) -> Character:
    seedance = existing_seedance or {}
    if seedance.get("status") not in {"active", "processing"}:
        try:
            seedance = await register_virtual_character(name, image_url)
        except Exception as exc:
            seedance = {
                "provider": "toapis",
                "type": "private-avatar",
                "status": "failed",
                "error": str(exc)[:500],
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
    db.add(item)
    await db.commit()
    await db.refresh(item)
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
    try:
        stored = await store_reference_image(file, "outfit-models")
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        return fail(f"模特上传失败：{exc}")
    item = OutfitModel(
        user_id=user_id,
        name=((name or file.filename or "我的模特").rsplit(".", 1)[0].strip() or "我的模特")[:100],
        image_url=stored["url"],
        object_key=stored["object_key"],
        width=stored["width"],
        height=stored["height"],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
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
    try:
        for item in items:
            await refresh_virtual_character(item)
        await db.commit()
    except ToApisError:
        pass
    return success([reference_payload(item, "character") for item in items])


@router.post("/characters")
async def upload_character(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        stored = await store_reference_image(file, "characters")
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        return fail(f"角色上传失败：{exc}")
    character_name = ((name or file.filename or "我的角色").rsplit(".", 1)[0].strip() or "我的角色")[:100]
    item = await create_character_item(
        name=character_name,
        image_url=stored["url"],
        object_key=stored["object_key"],
        width=stored["width"],
        height=stored["height"],
        user_id=user_id,
        db=db,
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
        return fail("素材不存在")
    if asset.media_type != "image":
        return fail("仅图片素材可注册为角色")
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
        return fail("角色不存在")
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
        item.character_metadata = {
            **(item.character_metadata or {}),
            "seedance": {**((item.character_metadata or {}).get("seedance") or {}), "status": "failed", "error": str(exc)[:500]},
        }
        await db.commit()
        return fail(str(exc), reference_payload(item, "character"))


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
    try:
        stored = await store_reference_image(file, "garments")
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        return fail(f"服饰上传失败：{exc}")
    item = Garment(
        user_id=user_id,
        name=((name or file.filename or "我的服饰").rsplit(".", 1)[0].strip() or "我的服饰")[:100],
        image_url=stored["url"],
        object_key=stored["object_key"],
        width=stored["width"],
        height=stored["height"],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return success(reference_payload(item, "garment"))
