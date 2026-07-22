import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models import GenerationTask
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
                await _update_by_id(
                    task_uuid,
                    status="succeeded",
                    progress=100,
                    result={"type": "image", "data": [{"url": url} for url in stored_urls]},
                    finished_at=datetime.now(UTC),
                )
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


async def _update(db: AsyncSession, task: GenerationTask, **values):
    for key, value in values.items():
        setattr(task, key, value)
    await db.commit()
