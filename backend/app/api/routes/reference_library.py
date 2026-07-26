import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import Character, OutfitModel
from app.schemas.response import fail, success
from app.services.image_processing import normalize_image
from app.services.storage import OssStorage

router = APIRouter()

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024


def reference_payload(item: OutfitModel | Character, resource_type: str) -> dict[str, Any]:
    metadata = item.model_metadata if resource_type == "model" else item.character_metadata
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
    items = await db.scalars(
        select(Character)
        .where(
            Character.active.is_(True),
            or_(Character.user_id.is_(None), Character.user_id == user_id),
        )
        .order_by(Character.user_id.is_not(None), Character.sort_order, Character.created_at)
    )
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
    item = Character(
        user_id=user_id,
        name=((name or file.filename or "我的角色").rsplit(".", 1)[0].strip() or "我的角色")[:100],
        image_url=stored["url"],
        object_key=stored["object_key"],
        width=stored["width"],
        height=stored["height"],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return success(reference_payload(item, "character"))
