import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select

from app.core.database import SessionLocal
from app.core.errors import diagnostic_snapshot
from app.core.generation_state import TERMINAL_TASK_STATUSES
from app.models import GenerationTask
from app.providers.toapis import ToApisError
from app.services.task_lifecycle import (
    complete_task, complete_text_task, fail_task, update_task,
    fail_task_in_transaction, lock_task, transition_task,
    MAX_RECOVERY_ATTEMPTS,
)
from arq import Retry

# Public compatibility exports for existing callers.
__all__ = [
    "complete_task", "complete_text_task", "fail_task", "update_task",
    "poll_generation", "result_urls", "result_last_frame_url",
    "compensate_stale_generation_tasks", "GenerationPollTimeout", "run_queued_worker",
]


class GenerationPollTimeout(RuntimeError):
    pass


class GenerationProviderFailed(ToApisError):
    """A provider query explicitly confirmed generation failure."""


logger = logging.getLogger(__name__)


async def run_queued_worker(run, task_id: str):
    try:
        await run(task_id)
    except Exception:
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, uuid.UUID(task_id))
            if task and task.status == "queued" and task.recovery_attempts < MAX_RECOVERY_ATTEMPTS:
                raise Retry(defer=30)
        raise
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, uuid.UUID(task_id))
        if task and task.status == "queued" and task.recovery_attempts < MAX_RECOVERY_ATTEMPTS:
            raise Retry(defer=30)


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
    worker_token: str | None = None,
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
        if await update_task(task_id, progress=progress, worker_token=worker_token) is False:
            from app.services.provider_execution import SubmissionNeedsReview
            raise SubmissionNeedsReview("任务已暂停或交由其他 worker 处理")
        if state.get("status") == "completed":
            return state
        if state.get("status") == "failed":
            error = state.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise GenerationProviderFailed(message or f"{media_label}生成失败")
    raise GenerationPollTimeout(f"{media_label}生成超时")


async def compensate_stale_generation_tasks(ctx) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=30)
    async with SessionLocal() as db:
        task_ids = list(
            await db.scalars(
                select(GenerationTask.id).where(
                    GenerationTask.credit_status == "frozen",
                    or_(
                        (GenerationTask.status == "queued") & (
                            (GenerationTask.updated_at < cutoff)
                            | and_(
                                GenerationTask.submission_started_at.is_(None),
                                GenerationTask.retry_count == 0,
                                GenerationTask.created_at < cutoff,
                            )
                        ),
                        (GenerationTask.status == "running") & (GenerationTask.updated_at < cutoff),
                    ),
                )
            )
        )
    for task_id in task_ids:
        async with SessionLocal() as db:
            task = await lock_task(db, task_id)
            if not task or task.status in TERMINAL_TASK_STATUSES:
                continue
            now = datetime.now(UTC)
            if task.worker_lease_until and task.worker_lease_until > now:
                continue
            last_activity = (
                task.created_at if not task.submission_started_at and not task.retry_count
                else task.updated_at
            )
            if last_activity >= cutoff:
                continue
            if task.task_type in {"image", "video", "audio"} and (
                task.provider_task_id or task.submission_started_at or task.provider_response
            ):
                if task.recovery_attempts >= MAX_RECOVERY_ATTEMPTS:
                    await transition_task(db, task.id, "needs_review", source="retry_limit")
                    task.error_message = "自动恢复次数已达上限，请人工核查"
                    await db.commit()
                    continue
                if ctx and ctx.get("redis"):
                    await transition_task(db, task.id, "queued", source="stale_recovery")
                    task.retry_count += 1
                    task.recovery_attempts += 1
                    task.error_message = "任务已恢复排队，核对上游结果"
                    await db.commit()
                    try:
                        await ctx["redis"].enqueue_job(
                            f"generate_{task.task_type}", str(task.id),
                            _job_id=f"generation:{task.id}:recovery:{task.retry_count}",
                        )
                    except Exception:
                        logger.exception("stale_recovery_enqueue_failed", extra={"task_id": str(task.id)})
                else:
                    await transition_task(db, task.id, "needs_review", source="stale_recovery")
                    task.error_message = "上游结果尚未确认，等待恢复查询"
                    await db.commit()
                continue
            error = GenerationPollTimeout("生成任务超时")
            await fail_task_in_transaction(
                db, task.id, "timeout", str(error), diagnostic_snapshot(error, "poll"),
                source="stale_timeout",
            )
            await db.commit()
