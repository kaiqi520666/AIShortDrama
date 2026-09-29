import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import or_, select

from app.core.database import SessionLocal
from app.core.errors import diagnostic_snapshot
from app.models import Asset, GenerationTask, Workspace
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


def result_last_frame_url(state: dict[str, Any]) -> str | None:
    result = state.get("result") or {}
    candidates = [result.get("last_frame_url"), result.get("last_frame")]
    candidates.extend(
        item.get("last_frame_url") or item.get("last_frame")
        for item in result.get("data") or []
        if isinstance(item, dict)
    )
    return next((url for url in candidates if isinstance(url, str) and url), None)


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
    result_extra: dict[str, Any] | None = None,
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
        if result_extra:
            task.result.update(result_extra)
        if media_type == "image":
            workspace = await db.get(Workspace, task.workspace_id)
            if workspace:
                workspace.thumbnail_url = urls[0]
        await settle_task_credits(db, task, original_duration=original_duration)
        await db.commit()


async def fail_task(
    task_id: uuid.UUID,
    status: str,
    message: str,
    diagnostic: dict[str, Any] | None = None,
) -> None:
    async with SessionLocal() as db:
        task = await db.scalar(
            select(GenerationTask).where(GenerationTask.id == task_id).with_for_update()
        )
        if not task or task.status in {"succeeded", "failed", "timeout", "cancelled"}:
            return
        task.status = status
        task.error_message = message[:2000]
        task.diagnostic_snapshot = diagnostic
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


async def compensate_stale_generation_tasks(ctx) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=30)
    async with SessionLocal() as db:
        tasks = list(
            await db.scalars(
                select(GenerationTask).where(
                    GenerationTask.credit_status == "frozen",
                    or_(
                        (GenerationTask.status == "queued") & (GenerationTask.created_at < cutoff),
                        (GenerationTask.status == "running") & (GenerationTask.updated_at < cutoff),
                    ),
                )
            )
        )
    for task in tasks:
        if task.task_type == "video" and task.provider_task_id:
            await update_task(
                task.id,
                status="queued",
                error_message="视频任务已恢复排队，继续查询上游结果",
            )
            if ctx and ctx.get("redis"):
                await ctx["redis"].enqueue_job("generate_video", str(task.id))
            continue
        error = GenerationPollTimeout("生成任务超时")
        await fail_task(
            task.id,
            "timeout",
            str(error),
            diagnostic_snapshot(error, "poll"),
        )
