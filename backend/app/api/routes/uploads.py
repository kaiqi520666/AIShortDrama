import logging
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, RequestError, ServiceUnavailableError, public_error_message
from app.core.identity import get_current_user_id
from app.models import Asset, Workspace
from app.schemas.response import success
from app.services.media_upload import MEDIA_UPLOAD_RULES, MediaUploadService
from app.services.storage import OssStorage

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_RULES = MEDIA_UPLOAD_RULES


def get_media_upload_service() -> MediaUploadService:
    return MediaUploadService(storage_factory=OssStorage)


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
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
    )
    if not workspace:
        raise NotFoundError("工作台不存在")

    filename = file.filename or f"未命名{media_type}"
    service = get_media_upload_service()
    try:
        stored = await service.store(
            file, media_type, f"uploads/{media_type}s", rules=UPLOAD_RULES
        )
    except ValueError as exc:
        raise RequestError(str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Media upload failed", extra={"workspace_id": str(workspace_id), "node_id": node_id}
        )
        raise ServiceUnavailableError(public_error_message(exc, "上传服务暂时不可用")) from exc

    asset = Asset(
        user_id=user_id,
        workspace_id=workspace_id,
        node_id=node_id,
        media_type=media_type,
        source_type="upload",
        name=filename[:255],
        object_key=stored.object_key,
        url=stored.url,
        mime_type=stored.content_type,
        byte_size=stored.byte_size,
        width=stored.width or width,
        height=stored.height or height,
        duration=duration,
        asset_metadata={},
    )
    db.add(asset)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        try:
            await service.delete(stored)
        except Exception:
            logger.exception("Failed to delete orphan upload", extra={"object_key": stored.object_key})
        logger.exception("Failed to persist uploaded media", extra={"workspace_id": str(workspace_id)})
        raise ServiceUnavailableError("上传服务暂时不可用") from exc
    await db.refresh(asset)
    return success(
        {
            "id": str(asset.id),
            "url": stored.url,
            "object_key": stored.object_key,
            "content_type": stored.content_type,
            "size": stored.byte_size,
            "width": asset.width,
            "height": asset.height,
            "name": asset.name,
            "media_type": media_type,
            "source_type": asset.source_type,
        }
    )
