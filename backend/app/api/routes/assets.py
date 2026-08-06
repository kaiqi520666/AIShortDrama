import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import (
    NotFoundError,
    RequestError,
    ServiceUnavailableError,
    UpstreamMediaError,
    public_error_message,
)
from app.core.identity import get_current_user_id
from app.models import Asset
from app.providers.toapis import ToApisProvider
from app.schemas.asset import AssetPrivateAvatarRequest, AssetUpdate, ComposeImageBoardRequest
from app.services.image_processing import (
    OutfitBoardDownloadError,
    compose_outfit_board,
    download_outfit_board_images,
)
from app.services.storage import OssStorage
from app.schemas.response import success

router = APIRouter()
logger = logging.getLogger(__name__)


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


def private_avatar_metadata(data: dict[str, Any]) -> dict[str, Any]:
    asset_id = data.get("asset_id") or data.get("id")
    return {
        "provider": "toapis",
        "type": "private-avatar",
        "group_id": data.get("group_id"),
        "asset_id": asset_id,
        "asset_url": data.get("asset_url") or (f"asset://{asset_id}" if asset_id else None),
        "status": str(data.get("status") or "processing").lower(),
    }


@router.get("")
async def list_assets(
    media_type: Literal["image", "video", "audio"] | None = Query(default=None, alias="type"),
    workspace_id: uuid.UUID | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    query = select(Asset).where(Asset.user_id == user_id, Asset.deleted_at.is_(None))
    if media_type:
        query = query.where(Asset.media_type == media_type)
    if workspace_id:
        query = query.where(Asset.workspace_id == workspace_id)
    query = query.order_by(Asset.created_at.desc(), Asset.id.desc()).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    assets = (await db.scalars(query)).all()
    return success([asset_payload(item) for item in assets])


@router.post("/compose-board")
async def compose_board(
    payload: ComposeImageBoardRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    try:
        workspace_id = uuid.UUID(payload.workspace_id)
        asset_uuid_list = [uuid.UUID(asset_id) for asset_id in payload.asset_ids]
    except ValueError:
        raise RequestError("工作台或图片资产 ID 无效")

    assets = (
        await db.scalars(
            select(Asset).where(
                Asset.id.in_(asset_uuid_list),
                Asset.user_id == user_id,
                Asset.workspace_id == workspace_id,
                Asset.media_type == "image",
                Asset.deleted_at.is_(None),
            )
        )
    ).all()
    by_id = {str(asset.id): asset for asset in assets}
    if len(by_id) != 6 or any(asset_id not in by_id for asset_id in payload.asset_ids):
        raise RequestError("只能合成当前工作台中属于自己的 6 张图片")

    stream = None
    images = []
    storage = None
    object_key = None
    committed = False
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            images = await download_outfit_board_images(
                [by_id[asset_id].url for asset_id in payload.asset_ids], client
            )
        stream, width, height = compose_outfit_board(images)
        object_key = f"generations/images/outfit-board-{uuid.uuid4()}.jpg"
        storage = OssStorage()
        url = await storage.store_upload(object_key, stream, "image/jpeg")
        board = Asset(
            user_id=user_id,
            workspace_id=workspace_id,
            node_id=payload.node_id,
            media_type="image",
            source_type="composition",
            name="服饰穿搭参考总览",
            object_key=object_key,
            url=url,
            mime_type="image/jpeg",
            byte_size=stream.getbuffer().nbytes,
            width=width,
            height=height,
            asset_metadata={
                "type": "outfit-board",
                "source_asset_ids": payload.asset_ids,
                "layout": "2x3",
                "aspect_ratio": "9:16",
            },
        )
        db.add(board)
        await db.commit()
        committed = True
        await db.refresh(board)
        return success(asset_payload(board))
    except Exception as exc:
        if not committed:
            await db.rollback()
            if object_key and storage:
                try:
                    await storage.delete_object(object_key)
                except Exception:
                    logger.exception("Failed to delete orphan outfit board object", extra={"object_key": object_key})
        if isinstance(exc, OutfitBoardDownloadError):
            error_type = UpstreamMediaError if exc.status_code == 502 else RequestError
            raise error_type(str(exc)) from exc
        logger.exception("Failed to compose outfit board")
        raise ServiceUnavailableError(
            public_error_message(exc, "服饰总览图服务暂时不可用")
        ) from exc
    finally:
        for image in images:
            image.close()
        if stream:
            stream.close()


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    asset = await owned_asset(db, asset_id, user_id)
    if not asset:
        raise NotFoundError("资产不存在")
    asset.name = payload.name
    await db.commit()
    await db.refresh(asset)
    return success(asset_payload(asset))


@router.post("/{asset_id}/private-avatar")
async def register_private_avatar(
    asset_id: uuid.UUID,
    payload: AssetPrivateAvatarRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    asset = await owned_asset(db, asset_id, user_id)
    if not asset:
        raise NotFoundError("资产不存在")
    if asset.media_type != "image":
        raise RequestError("仅图片资产可注册为虚拟人像素材")

    seedance = (asset.asset_metadata or {}).get("seedance") or {}
    try:
        async with ToApisProvider() as provider:
            if seedance.get("status") == "processing" and seedance.get("asset_id"):
                state = await provider.get_private_avatar(seedance["asset_id"])
                seedance = private_avatar_metadata(
                    {**seedance, **state, "group_id": seedance.get("group_id")}
                )
            elif seedance.get("status") != "active":
                group_id = payload.group_id or seedance.get("group_id")
                if not group_id:
                    group = await provider.create_private_avatar_group(asset.name)
                    group_id = group.get("group_id")
                if not group_id:
                    raise RuntimeError("ToAPIs 未返回虚拟人像组 ID")
                uploaded = await provider.upload_private_avatar(group_id, asset.url, asset.name)
                seedance = private_avatar_metadata({**uploaded, "group_id": group_id})
        asset.asset_metadata = {**(asset.asset_metadata or {}), "seedance": seedance}
        await db.commit()
        await db.refresh(asset)
        return success(asset_payload(asset))
    except Exception as exc:
        message = public_error_message(exc, "虚拟人像服务暂时不可用")
        logger.exception("Private avatar registration failed", extra={"asset_id": str(asset.id)})
        asset.asset_metadata = {
            **(asset.asset_metadata or {}),
            "seedance": {**seedance, "status": "failed", "error": message},
        }
        await db.commit()
        raise ServiceUnavailableError(message, asset_payload(asset)) from exc


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
        raise NotFoundError("资产不存在")
    asset.deleted_at = datetime.now(UTC)
    await db.commit()
    return success({"id": str(asset.id)})
