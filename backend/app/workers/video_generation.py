import uuid
from datetime import UTC, datetime

from app.core.database import SessionLocal
from app.models import GenerationTask
from app.providers.toapis import ToApisError, ToApisProvider
from app.services.storage import OssStorage
from app.workers.generation import (
    GenerationPollTimeout,
    complete_task,
    fail_task,
    poll_generation,
    result_urls,
    update_task,
)


async def generate_video(_ctx, task_id: str):
    await run_video_generation(task_id)


async def run_video_generation(
    task_id: str,
    provider: ToApisProvider | None = None,
    storage: OssStorage | None = None,
    poll_interval: int = 10,
    max_polls: int = 120,
):
    task_uuid = uuid.UUID(task_id)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_uuid)
        if not task or task.status in {"succeeded", "failed", "timeout", "cancelled"}:
            return
        payload = task.request_snapshot
        task.status = "running"
        task.progress = 0
        task.started_at = datetime.now(UTC)
        await db.commit()

    owns_provider = provider is None
    try:
        provider = provider or ToApisProvider()
        storage = storage or OssStorage()
        submitted = await provider.submit_video(payload)
        provider_task_id = submitted.get("id")
        if not provider_task_id:
            raise ToApisError("ToAPIs 未返回任务 ID")
        await update_task(task_uuid, provider_task_id=provider_task_id)
        state = await poll_generation(
            provider.get_video_task,
            provider_task_id,
            task_uuid,
            "视频",
            poll_interval,
            max_polls,
        )
        urls = result_urls(state, "视频")
        await complete_task(task_uuid, "video", await storage.store_remote_videos(task_id, urls))
    except GenerationPollTimeout as exc:
        await fail_task(task_uuid, "timeout", str(exc))
    except Exception as exc:
        await fail_task(
            task_uuid,
            "failed",
            exc.public_message if isinstance(exc, ToApisError) else str(exc),
        )
        raise
    finally:
        if owns_provider and provider:
            await provider.client.aclose()
