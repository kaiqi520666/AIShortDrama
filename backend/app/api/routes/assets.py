import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import Asset
from app.schemas.response import success

router = APIRouter()


def asset_payload(asset: Asset) -> dict[str, Any]:
    return {
        "id": str(asset.id),
        "workspace_id": str(asset.workspace_id) if asset.workspace_id else None,
        "generation_task_id": (
            str(asset.generation_task_id) if asset.generation_task_id else None
        ),
        "node_id": asset.node_id,
        "media_type": asset.media_type,
        "source_type": asset.source_type,
        "name": asset.name,
        "object_key": asset.object_key,
        "url": asset.url,
        "mime_type": asset.mime_type,
        "byte_size": asset.byte_size,
        "width": asset.width,
        "height": asset.height,
        "duration": asset.duration,
        "metadata": asset.asset_metadata,
        "created_at": asset.created_at.isoformat(),
    }


@router.get("")
async def list_assets(
    media_type: Literal["image", "video", "audio"] | None = Query(default=None, alias="type"),
    workspace_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    query = select(Asset).where(Asset.user_id == user_id, Asset.deleted_at.is_(None))
    if media_type:
        query = query.where(Asset.media_type == media_type)
    if workspace_id:
        query = query.where(Asset.workspace_id == workspace_id)
    assets = (await db.scalars(query.order_by(Asset.created_at.desc()))).all()
    return success([asset_payload(item) for item in assets])
