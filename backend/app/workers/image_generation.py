import asyncio
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models import Asset, GenerationTask
from app.providers.toapis import ToApisError, ToApisProvider
from app.services.storage import OssStorage


async def generate_image(_ctx, task_id: str):
    await run_image_generation(task_id)


async def run_image_generation(
    task_id: str,
    provider: ToApisProvider | None = None,
    storage: OssStorage | None = None,
    poll_interval: int = 5,
    max_polls: int = 72,
):
    task_uuid = uuid.UUID(task_id)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_uuid)
        if not task or task.status in {"succeeded", "cancelled"}:
            return
        payload = task.request_snapshot
        await _update(db, task, status="running", progress=0, started_at=datetime.now(UTC))

    owns_provider = provider is None
    try:
        provider = provider or ToApisProvider()
        storage = storage or OssStorage()
        submitted = await provider.submit_image(payload)
        provider_task_id = submitted.get("id")
        if not provider_task_id:
            raise ToApisError("ToAPIs 未返回任务 ID")
        await _update_by_id(task_uuid, provider_task_id=provider_task_id)

        for _ in range(max_polls):
            await asyncio.sleep(poll_interval)
            state = await provider.get_image_task(provider_task_id)
            progress = max(0, min(100, int(state.get("progress") or 0)))
            if state.get("status") == "completed":
                urls = [item.get("url") for item in state.get("result", {}).get("data", [])]
                urls = [url for url in urls if url]
                if not urls:
                    raise ToApisError("ToAPIs 未返回图片地址")
                stored_urls = await storage.store_remote_images(task_id, urls)
                await _complete_task(task_uuid, stored_urls)
                return
            if state.get("status") == "failed":
                error = state.get("error") or {}
                raise ToApisError(error.get("message") or "图片生成失败")
            await _update_by_id(task_uuid, progress=progress)

        await _update_by_id(
            task_uuid,
            status="timeout",
            error_message="图片生成超时",
            finished_at=datetime.now(UTC),
        )
    except Exception as exc:
        await _update_by_id(
            task_uuid,
            status="failed",
            error_message=str(exc)[:2000],
            finished_at=datetime.now(UTC),
        )
        raise
    finally:
        if owns_provider and provider:
            await provider.client.aclose()


async def _update_by_id(task_id: uuid.UUID, **values):
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        if task:
            await _update(db, task, **values)


async def _complete_task(task_id: uuid.UUID, urls: list[str]):
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        if not task:
            return
        task.status = "succeeded"
        task.progress = 100
        task.result = {"type": "image", "data": [{"url": url} for url in urls]}
        task.finished_at = datetime.now(UTC)
        for index, url in enumerate(urls, start=1):
            db.add(
                Asset(
                    user_id=task.user_id,
                    workspace_id=task.workspace_id,
                    generation_task_id=task.id,
                    node_id=task.node_id,
                    media_type="image",
                    source_type="generation",
                    name=f"生成图片 {index}",
                    object_key=urlparse(url).path.lstrip("/") or None,
                    url=url,
                )
            )
        await db.commit()


async def _update(db: AsyncSession, task: GenerationTask, **values):
    for key, value in values.items():
        setattr(task, key, value)
    await db.commit()
