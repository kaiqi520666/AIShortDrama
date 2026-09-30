import logging
import uuid
from datetime import UTC, datetime

from app.core.database import SessionLocal
from app.core.errors import diagnostic_snapshot, public_error_message
from app.core.generation_state import TERMINAL_TASK_STATUSES, transition_task
from app.models import GenerationTask
from app.providers.protocols import ImageVideoProvider
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


logger = logging.getLogger(__name__)


async def generate_image(_ctx, task_id: str):
    await run_image_generation(task_id)


async def run_image_generation(
    task_id: str,
    provider: ImageVideoProvider | None = None,
    storage: OssStorage | None = None,
    poll_interval: int = 5,
    max_polls: int = 120,
):
    task_uuid = uuid.UUID(task_id)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_uuid)
        if not task or task.status in TERMINAL_TASK_STATUSES:
            return
        payload = task.request_snapshot
        transition_task(task, "running", progress=0)
        task.started_at = datetime.now(UTC)
        await db.commit()

    owns_provider = provider is None
    stage = "submit"
    try:
        provider = provider or ToApisProvider()
        storage = storage or OssStorage()
        submitted = await provider.submit_image(payload)
        provider_task_id = submitted.get("id")
        if not provider_task_id:
            raise ToApisError("ToAPIs 未返回任务 ID")
        await update_task(task_uuid, provider_task_id=provider_task_id)
        stage = "poll"
        state = await poll_generation(
            provider.get_image_task,
            provider_task_id,
            task_uuid,
            "图片",
            poll_interval,
            max_polls,
        )
        urls = result_urls(state, "图片")
        stage = "storage"
        stored_images = await storage.store_remote_images(task_id, urls)
        stage = "billing"
        await complete_task(task_uuid, "image", stored_images)
    except GenerationPollTimeout as exc:
        await fail_task(
            task_uuid,
            "timeout",
            str(exc),
            diagnostic_snapshot(exc, "poll"),
        )
    except Exception as exc:
        logger.exception("Image generation failed", extra={"task_id": str(task_uuid)})
        await fail_task(
            task_uuid,
            "failed",
            public_error_message(exc, "图片生成服务暂时不可用"),
            diagnostic_snapshot(exc, stage),
        )
        raise
    finally:
        if owns_provider and provider:
            await provider.client.aclose()
