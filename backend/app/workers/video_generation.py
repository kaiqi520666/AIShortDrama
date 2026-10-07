import logging
import uuid

from app.core.errors import diagnostic_snapshot, public_error_message
from app.providers.protocols import ImageVideoProvider
from app.providers.toapis import ToApisError
from app.providers.registry import create_generation_provider, adapt_generation_provider
from app.services.provider_execution import (
    SubmissionNeedsReview, persist_provider_result, submit_provider_task,
)
from app.services.task_lifecycle import mark_needs_review, queue_task, start_task
from app.services.storage import OssStorage
from app.workers.generation import (
    GenerationPollTimeout,
    GenerationProviderFailed,
    complete_task,
    fail_task,
    poll_generation,
    result_last_frame_url,
    result_urls,
    run_queued_worker,
)


logger = logging.getLogger(__name__)


async def generate_video(_ctx, task_id: str):
    await run_queued_worker(run_video_generation, task_id)


async def run_video_generation(
    task_id: str,
    provider: ImageVideoProvider | None = None,
    storage: OssStorage | None = None,
    poll_interval: int = 10,
    max_polls: int = 120,
):
    task_uuid = uuid.UUID(task_id)
    task = await start_task(task_uuid)
    if task is None:
        return
    token = task.worker_lease_token
    provider_task_id = task.provider_task_id

    owns_provider = provider is None
    stage = "recover" if task.submission_started_at or task.provider_task_id or task.provider_response else "submit"
    try:
        provider = (
            adapt_generation_provider(provider, "video") if provider is not None
            else create_generation_provider(task.provider, "video")
        )
        submitted = await submit_provider_task(task, provider)
        provider_task_id = submitted.get("id") or provider_task_id
        if submitted.get("status") == "completed":
            state = submitted
        else:
            if not provider_task_id:
                raise SubmissionNeedsReview("上游响应缺少任务 ID")
            stage = "poll"
            state = await poll_generation(
                provider.get_task, provider_task_id, task_uuid, "视频",
                poll_interval, max_polls, worker_token=token,
            )
        stage = "storage"
        await persist_provider_result(task, state)
        urls = result_urls(state, "视频")
        storage = storage or OssStorage()
        stored_videos = await storage.store_remote_videos(task_id, urls)
        last_frame_url = result_last_frame_url(state)
        stored_last_frame = await storage.store_remote_images(task_id, [last_frame_url]) if last_frame_url else None
        stage = "billing"
        await complete_task(
            task_uuid,
            "video",
            stored_videos,
            worker_token=token,
            result_extra={"last_frame_url": stored_last_frame[0]} if stored_last_frame else None,
        )
    except SubmissionNeedsReview as exc:
        await mark_needs_review(task_uuid, str(exc), worker_token=token)
    except GenerationPollTimeout as exc:
        await queue_task(task_uuid, str(exc), diagnostic_snapshot(exc, "poll"), worker_token=token)
    except ToApisError as exc:
        if stage in {"recover", "storage", "billing"}:
            await queue_task(
                task_uuid, "上游结果恢复暂时失败，等待重试",
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        elif stage == "poll" and not isinstance(exc, GenerationProviderFailed):
            await queue_task(
                task_uuid, "上游任务查询暂时失败，请稍后重试",
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        elif exc.retryable and stage == "submit":
            await mark_needs_review(
                task_uuid, "上游提交结果未知，请人工核对后再处理",
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        else:
            await fail_task(
                task_uuid, "failed", public_error_message(exc, "视频生成服务暂时不可用"),
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        raise
    except Exception as exc:
        logger.exception("Video generation failed", extra={"task_id": str(task_uuid)})
        if stage == "recover":
            await queue_task(
                task_uuid, "上游结果恢复暂时失败，等待重试",
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        elif stage == "submit" and task.submission_started_at:
            await mark_needs_review(task_uuid, "上游提交结果未知，请人工核对后再处理", worker_token=token)
        elif stage in {"poll", "storage", "billing"}:
            await queue_task(
                task_uuid, "生成结果处理失败，等待重试", diagnostic_snapshot(exc, stage), worker_token=token,
            )
        else:
            await fail_task(
                task_uuid, "failed", public_error_message(exc, "视频生成服务暂时不可用"),
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        raise
    finally:
        if owns_provider and provider:
            await provider.aclose()
