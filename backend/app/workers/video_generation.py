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
    result_last_frame_url,
    result_urls,
    update_task,
)


logger = logging.getLogger(__name__)


async def generate_video(_ctx, task_id: str):
    await run_video_generation(task_id)


async def run_video_generation(
    task_id: str,
    provider: ImageVideoProvider | None = None,
    storage: OssStorage | None = None,
    poll_interval: int = 10,
    max_polls: int = 120,
):
    task_uuid = uuid.UUID(task_id)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_uuid)
        if not task or task.status in TERMINAL_TASK_STATUSES:
            return
        payload = task.request_snapshot
        provider_task_id = task.provider_task_id
        transition_task(task, "running", progress=0 if not provider_task_id else None)
        task.started_at = datetime.now(UTC)
        await db.commit()

    owns_provider = provider is None
    stage = "submit"
    try:
        provider = provider or ToApisProvider()
        storage = storage or OssStorage()
        if not provider_task_id:
            submitted = await provider.submit_video(payload)
            provider_task_id = submitted.get("id")
            if not provider_task_id:
                raise ToApisError("ToAPIs 未返回任务 ID")
            await update_task(task_uuid, provider_task_id=provider_task_id)
        stage = "poll"
        state = await poll_generation(
            provider.get_video_task,
            provider_task_id,
            task_uuid,
            "视频",
            poll_interval,
            max_polls,
        )
        urls = result_urls(state, "视频")
        stage = "storage"
        stored_videos = await storage.store_remote_videos(task_id, urls)
        last_frame_url = result_last_frame_url(state)
        stored_last_frame = await storage.store_remote_images(task_id, [last_frame_url]) if last_frame_url else None
        stage = "billing"
        await complete_task(
            task_uuid,
            "video",
            stored_videos,
            result_extra={"last_frame_url": stored_last_frame[0]} if stored_last_frame else None,
        )
    except GenerationPollTimeout as exc:
        await update_task(task_uuid, status="queued", error_message=str(exc), diagnostic_snapshot=diagnostic_snapshot(exc, "poll"))
    except ToApisError as exc:
        if exc.retryable and provider_task_id:
            await update_task(task_uuid, status="queued", error_message="上游任务查询暂时失败，请稍后重试", diagnostic_snapshot=diagnostic_snapshot(exc, stage))
        elif exc.retryable:
            await update_task(task_uuid, status="needs_review", error_message="上游提交结果未知，请人工核对后再处理", diagnostic_snapshot=diagnostic_snapshot(exc, stage))
        else:
            await fail_task(
                task_uuid,
                "failed",
                public_error_message(exc, "视频生成服务暂时不可用"),
                diagnostic_snapshot(exc, stage),
            )
        raise
    except Exception as exc:
        logger.exception("Video generation failed", extra={"task_id": str(task_uuid)})
        await fail_task(
            task_uuid,
            "failed",
            public_error_message(exc, "视频生成服务暂时不可用"),
            diagnostic_snapshot(exc, stage),
        )
        raise
    finally:
        if owns_provider and provider:
            await provider.client.aclose()
