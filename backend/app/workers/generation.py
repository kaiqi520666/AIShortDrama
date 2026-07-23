import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.core.database import SessionLocal
from app.models import Asset, GenerationTask
from app.providers.toapis import ToApisError


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


async def complete_task(task_id: uuid.UUID, media_type: str, urls: list[str]):
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        if not task:
            return
        task.status = "succeeded"
        task.progress = 100
        task.result = {"type": media_type, "data": [{"url": url} for url in urls]}
        task.finished_at = datetime.now(UTC)
        duration = task.request_snapshot.get("duration") if media_type == "video" else None
        for index, url in enumerate(urls, start=1):
            video_mime_types = {".mov": "video/quicktime", ".webm": "video/webm"}
            extension = urlparse(url).path.rsplit(".", 1)[-1].lower()
            mime_type = video_mime_types.get(f".{extension}", "video/mp4")
            db.add(
                Asset(
                    user_id=task.user_id,
                    workspace_id=task.workspace_id,
                    generation_task_id=task.id,
                    node_id=task.node_id,
                    media_type=media_type,
                    source_type="generation",
                    name=f"生成{'视频' if media_type == 'video' else '图片'} {index}",
                    object_key=urlparse(url).path.lstrip("/") or None,
                    url=url,
                    mime_type=mime_type if media_type == "video" else None,
                    duration=duration if isinstance(duration, int) and duration > 0 else None,
                )
            )
        await db.commit()
