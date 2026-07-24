import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Asset, GenerationTask
from app.providers.toapis import ToApisError
from app.services.billing import refund_task_credits, settle_task_credits


class GenerationPollTimeout(RuntimeError):
    pass


def result_urls(state: dict[str, Any], media_label: str) -> list[str]:
    result = state.get("result") or {}
    urls = [item.get("url") for item in result.get("data") or [] if isinstance(item, dict)]
    urls = [url for url in urls if url]
    if not urls:
        raise ToApisError(f"ToAPIs 未返回{media_label}地址")
    return urls


async def poll_generation(
    fetch_task: Callable[[str], Awaitable[dict[str, Any]]],
    provider_task_id: str,
    task_id: uuid.UUID,
    media_label: str,
    poll_interval: int,
    max_polls: int,
) -> dict[str, Any]:
    for _ in range(max_polls):
        await asyncio.sleep(poll_interval)
        try:
            state = await fetch_task(provider_task_id)
        except ToApisError as exc:
            if exc.retryable:
                continue
            raise
        progress = max(0, min(100, int(state.get("progress") or 0)))
        await update_task(task_id, progress=progress)
        if state.get("status") == "completed":
            return state
        if state.get("status") == "failed":
            error = state.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise ToApisError(message or f"{media_label}生成失败")
    raise GenerationPollTimeout(f"{media_label}生成超时")


async def update_task(task_id: uuid.UUID, **values):
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        if not task:
            return
        for key, value in values.items():
            setattr(task, key, value)
        await db.commit()


async def complete_task(
    task_id: uuid.UUID,
    media_type: str,
    urls: list[str],
    duration: float | None = None,
    original_duration: float | None = None,
    mime_type: str | None = None,
):
    async with SessionLocal() as db:
        task = await db.scalar(
            select(GenerationTask).where(GenerationTask.id == task_id).with_for_update()
        )
        if not task or task.status in {"succeeded", "failed", "timeout", "cancelled"}:
            return
        task.status = "succeeded"
        task.progress = 100
        task.finished_at = datetime.now(UTC)
        asset_duration = duration
        if asset_duration is None and media_type == "video":
            asset_duration = task.request_snapshot.get("duration")
        assets = []
        for index, url in enumerate(urls, start=1):
            video_mime_types = {".mov": "video/quicktime", ".webm": "video/webm"}
            extension = urlparse(url).path.rsplit(".", 1)[-1].lower()
            asset_mime_type = mime_type
            if media_type == "video":
                asset_mime_type = video_mime_types.get(f".{extension}", "video/mp4")
            media_name = {"image": "图片", "video": "视频", "audio": "音频"}[media_type]
            asset = Asset(
                user_id=task.user_id,
                workspace_id=task.workspace_id,
                generation_task_id=task.id,
                node_id=task.node_id,
                media_type=media_type,
                source_type="generation",
                name=f"生成{media_name} {index}",
                object_key=urlparse(url).path.lstrip("/") or None,
                url=url,
                mime_type=asset_mime_type,
                duration=asset_duration
                if isinstance(asset_duration, (int, float)) and asset_duration > 0
                else None,
            )
            db.add(asset)
            assets.append(asset)
        await db.flush()
        task.result = {
            "type": media_type,
            "data": [
                {
                    "url": url,
                    "asset_id": str(asset.id),
                    **({"duration": duration} if duration is not None else {}),
                    **({"mime_type": mime_type} if mime_type else {}),
                }
                for url, asset in zip(urls, assets, strict=True)
            ],
        }
        await settle_task_credits(db, task, original_duration=original_duration)
        await db.commit()


async def fail_task(task_id: uuid.UUID, status: str, message: str) -> None:
    async with SessionLocal() as db:
        task = await db.scalar(
            select(GenerationTask).where(GenerationTask.id == task_id).with_for_update()
        )
        if not task or task.status in {"succeeded", "failed", "timeout", "cancelled"}:
            return
        task.status = status
        task.error_message = message[:2000]
        task.finished_at = datetime.now(UTC)
        await refund_task_credits(db, task, f"{message[:220]}，退还冻结积分")
        await db.commit()


async def complete_text_task(task_id: uuid.UUID, content: str) -> None:
    async with SessionLocal() as db:
        task = await db.scalar(
            select(GenerationTask).where(GenerationTask.id == task_id).with_for_update()
        )
        if not task or task.status in {"succeeded", "failed", "timeout", "cancelled"}:
            return
        task.status = "succeeded"
        task.progress = 100
        task.result = {"type": "text", "content": content}
        task.finished_at = datetime.now(UTC)
        await settle_task_credits(db, task)
        await db.commit()


async def compensate_stale_generation_tasks(_ctx) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=30)
    async with SessionLocal() as db:
        task_ids = list(
            await db.scalars(
                select(GenerationTask.id).where(
                    GenerationTask.credit_status == "frozen",
                    GenerationTask.status.in_({"queued", "running"}),
                    GenerationTask.created_at < cutoff,
                )
            )
        )
    for task_id in task_ids:
        await fail_task(task_id, "timeout", "生成任务超时")
