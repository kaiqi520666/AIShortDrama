import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import Asset
from app.schemas.asset import AssetUpdate
from app.schemas.response import fail, success

router = APIRouter()


async def stream_remote(response: httpx.Response, client: httpx.AsyncClient):
    try:
        async for chunk in response.aiter_raw():
            yield chunk
    finally:
        await response.aclose()
        await client.aclose()


async def owned_asset(db: AsyncSession, asset_id: uuid.UUID, user_id: uuid.UUID) -> Asset | None:
    return await db.scalar(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.user_id == user_id,
            Asset.deleted_at.is_(None),
        )
    )


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
        "metadata": asset.asset_metadata or {},
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


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    asset = await owned_asset(db, asset_id, user_id)
    if not asset:
        return fail("资产不存在")
    asset.name = payload.name
    await db.commit()
    await db.refresh(asset)
    return success(asset_payload(asset))


@router.get("/{asset_id}/content")
async def stream_asset(
    asset_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    asset = await owned_asset(db, asset_id, user_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")

    headers = {"Accept-Encoding": "identity"}
    if request.headers.get("range"):
        headers["Range"] = request.headers["range"]
    client = httpx.AsyncClient(timeout=60, follow_redirects=True)
    try:
        response = await client.send(client.build_request("GET", asset.url, headers=headers), stream=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail="资产读取失败") from exc

    forwarded_headers = {
        name: response.headers[name]
        for name in ("accept-ranges", "content-length", "content-range", "etag", "last-modified")
        if name in response.headers
    }
    return StreamingResponse(
        stream_remote(response, client),
        status_code=response.status_code,
        media_type=asset.mime_type or response.headers.get("content-type"),
        headers=forwarded_headers,
    )


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    asset = await owned_asset(db, asset_id, user_id)
    if not asset:
        return fail("资产不存在")
    asset.deleted_at = datetime.now(UTC)
    await db.commit()
    return success({"id": str(asset.id)})
