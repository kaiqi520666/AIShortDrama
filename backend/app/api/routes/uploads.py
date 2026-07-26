import asyncio
import uuid
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import Asset, Workspace
from app.schemas.response import fail, success
from app.services.image_processing import normalize_image
from app.services.storage import OssStorage

router = APIRouter()

UPLOAD_RULES = {
    "image": {
        "max_size": 20 * 1024 * 1024,
        "content_types": {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        },
    },
    "video": {
        "max_size": 500 * 1024 * 1024,
        "content_types": {
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/webm": ".webm",
        },
    },
    "audio": {
        "max_size": 100 * 1024 * 1024,
        "content_types": {
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mp4": ".m4a",
        },
    },
}


@router.post("/{media_type}")
async def upload_media(
    media_type: str,
    file: UploadFile = File(...),
    workspace_id: uuid.UUID = Form(...),
    node_id: str = Form(..., min_length=1, max_length=64),
    width: int | None = Form(default=None),
    height: int | None = Form(default=None),
    duration: float | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    rule = UPLOAD_RULES.get(media_type)
    if not rule:
        return fail("不支持的媒体类型")
    if file.content_type not in rule["content_types"]:
        label = {"image": "图片", "video": "视频", "audio": "音频"}[media_type]
        return fail(f"不支持的{label}格式")
    if not file.size:
        return fail("上传文件不能为空")
    if file.size > rule["max_size"]:
        limit = (
            f"{rule['max_size'] // (1024 * 1024)}MB"
            if rule["max_size"] >= 1024 * 1024
            else f"{rule['max_size']}B"
        )
        return fail(f"文件不能超过 {limit}")

    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
    )
    if not workspace:
        return fail("工作台不存在")

    content_type = file.content_type
    byte_size = file.size
    filename = file.filename or f"未命名{media_type}"
    extension = rule["content_types"][content_type]
    date_path = datetime.now(UTC).strftime("%Y/%m/%d")
    object_key = f"uploads/{media_type}s/{date_path}/{uuid.uuid4().hex}{extension}"
    try:
        await file.seek(0)
        upload_stream = file.file
        if media_type == "image":
            normalized = await asyncio.to_thread(normalize_image, file.file, content_type)
            if normalized.size > rule["max_size"]:
                return fail(f"重编码后的图片不能超过 {rule['max_size'] // (1024 * 1024)}MB")
            upload_stream = normalized.stream
            byte_size = normalized.size
            width, height = normalized.width, normalized.height
        url = await OssStorage().store_upload(object_key, upload_stream, content_type)
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        return fail(f"上传失败：{exc}")
    finally:
        await file.close()

    asset = Asset(
        user_id=user_id,
        workspace_id=workspace_id,
        node_id=node_id,
        media_type=media_type,
        source_type="upload",
        name=filename[:255],
        object_key=object_key,
        url=url,
        mime_type=content_type,
        byte_size=byte_size,
        width=width,
        height=height,
        duration=duration,
        asset_metadata={},
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return success(
        {
            "id": str(asset.id),
            "url": url,
            "object_key": object_key,
            "content_type": content_type,
            "size": byte_size,
            "width": width,
            "height": height,
            "name": asset.name,
            "media_type": media_type,
            "source_type": asset.source_type,
        }
    )
