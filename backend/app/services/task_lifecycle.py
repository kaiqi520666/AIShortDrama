import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.generation_state import TERMINAL_TASK_STATUSES, transition_task as apply_transition
from app.core.observability import task_log_extra
from app.models import Asset, GenerationTask, Workspace
from app.services.billing import refund_task_credits, settle_task_credits

logger = logging.getLogger(__name__)
MAX_RECOVERY_ATTEMPTS = 4


def create_task(db: AsyncSession, **values) -> GenerationTask:
    task_id = values.pop("id", None) or uuid.uuid4()
    task = GenerationTask(
        id=task_id, client_request_id=str(task_id), status="queued", **values,
    )
    db.add(task)
    return task


async def lock_task(db: AsyncSession, task_id: uuid.UUID) -> GenerationTask | None:
    return await db.scalar(
        select(GenerationTask).where(GenerationTask.id == task_id).with_for_update()
        .execution_options(populate_existing=True)
    )


def _owns_task(task: GenerationTask, worker_token: str | None) -> bool:
    return worker_token is None or task.worker_lease_token == worker_token


def _transition(task: GenerationTask, status: str, source: str, **kwargs) -> None:
    previous = task.status
    apply_transition(task, status, **kwargs)
    task.updated_at = datetime.now(UTC)
    if status != "running":
        task.worker_lease_token = None
        task.worker_lease_until = None
    if status in TERMINAL_TASK_STATUSES:
        task.finished_at = datetime.now(UTC)
    elif status == "queued":
        task.finished_at = None
    logger.info(
        "generation_task_status_transition",
        extra=task_log_extra(
            task.id, from_status=previous, to_status=status, source=source,
            retry_count=task.retry_count,
            provider_task_id=task.provider_task_id, provider_request_id=task.provider_request_id,
        ),
    )


async def transition_task(
    db: AsyncSession, task_id: uuid.UUID, status: str, *, source: str,
    progress: int | None = None, manual: bool = False,
) -> GenerationTask | None:
    task = await lock_task(db, task_id)
    if not task:
        return None
    if task.status in TERMINAL_TASK_STATUSES and not (manual and task.status == "needs_review"):
        return task
    _transition(task, status, source, progress=progress, manual=manual)
    return task


async def start_task(task_id: uuid.UUID, *, source: str = "worker") -> GenerationTask | None:
    async with SessionLocal() as db:
        task = await lock_task(db, task_id)
        now = datetime.now(UTC)
        if not task or task.status in TERMINAL_TASK_STATUSES:
            return None
        if task.worker_lease_until and task.worker_lease_until > now:
            return None
        _transition(task, "running", source)
        task.started_at = task.started_at or now
        task.worker_lease_token = str(uuid.uuid4())
        task.worker_lease_until = now + timedelta(minutes=30)
        await db.commit()
        return task


async def update_task(
    task_id: uuid.UUID, *, source: str = "worker", worker_token: str | None = None, **values
):
    async with SessionLocal() as db:
        task = await lock_task(db, task_id)
        if not task or task.status in TERMINAL_TASK_STATUSES or not _owns_task(task, worker_token):
            return False
        status = values.pop("status", None)
        progress = values.pop("progress", None)
        if status is not None:
            _transition(task, status, source, progress=progress)
        elif progress is not None:
            if not 0 <= progress <= 100:
                raise ValueError("任务进度必须在 0 到 100 之间")
            task.progress = progress
        for key, value in values.items():
            if key not in {
                "provider_task_id", "provider_request_id", "provider_response",
                "submission_started_at", "error_message", "diagnostic_snapshot", "retry_count",
            }:
                raise ValueError(f"不允许直接更新任务字段：{key}")
            setattr(task, key, value)
        if task.status == "running" and task.worker_lease_token:
            task.worker_lease_until = datetime.now(UTC) + timedelta(minutes=30)
        await db.commit()
        return True


async def mark_needs_review(task_id: uuid.UUID, message: str, diagnostic=None, **kwargs):
    return await update_task(
        task_id, status="needs_review", error_message=message,
        diagnostic_snapshot=diagnostic, **kwargs,
    )


async def queue_task(task_id: uuid.UUID, message: str, diagnostic=None, **kwargs):
    async with SessionLocal() as db:
        task = await lock_task(db, task_id)
        worker_token = kwargs.get("worker_token")
        if not task or task.status in TERMINAL_TASK_STATUSES or not _owns_task(task, worker_token):
            return False
        task.recovery_attempts += 1
        status = "needs_review" if task.recovery_attempts >= MAX_RECOVERY_ATTEMPTS else "queued"
        _transition(task, status, kwargs.get("source", "worker_retry"))
        task.retry_count += 1
        task.error_message = message
        task.diagnostic_snapshot = diagnostic
        await db.commit()
        return True


async def fail_task_in_transaction(
    db: AsyncSession, task_id: uuid.UUID, status: str, message: str, diagnostic=None,
    *, source: str = "worker", manual: bool = False, worker_token: str | None = None,
) -> bool:
    if status not in {"failed", "timeout", "cancelled"}:
        raise ValueError("失败结算只能使用 failed、timeout 或 cancelled")
    task = await lock_task(db, task_id)
    if not task or not _owns_task(task, worker_token):
        return False
    if task.status in TERMINAL_TASK_STATUSES and not (manual and task.status == "needs_review"):
        return False
    _transition(task, status, source, manual=manual)
    task.error_message = message[:2000]
    task.diagnostic_snapshot = diagnostic
    await refund_task_credits(db, task, f"{message[:220]}，退还冻结积分")
    return True


async def complete_task(
    task_id: uuid.UUID,
    media_type: str,
    urls: list[str],
    duration: float | None = None,
    original_duration: float | None = None,
    mime_type: str | None = None,
    result_extra: dict[str, Any] | None = None,
    *,
    worker_token: str | None = None,
):
    async with SessionLocal() as db:
        task = await db.scalar(
            select(GenerationTask).where(GenerationTask.id == task_id).with_for_update()
        )
        if not task or task.status in TERMINAL_TASK_STATUSES or not _owns_task(task, worker_token):
            return
        _transition(task, "succeeded", "worker_complete", progress=100)
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
        task.provider_response = None
        task.error_message = None
        task.diagnostic_snapshot = None
        if media_type == "image":
            workspace = await db.get(Workspace, task.workspace_id)
            if workspace:
                workspace.thumbnail_url = urls[0]
        await settle_task_credits(db, task, original_duration=original_duration)
        logger.info(
            "generation_task_completed",
            extra=task_log_extra(task.id, media_type=media_type, asset_count=len(assets)),
        )
        await db.commit()


async def fail_task(
    task_id: uuid.UUID,
    status: str,
    message: str,
    diagnostic: dict[str, Any] | None = None,
    *,
    worker_token: str | None = None,
) -> None:
    async with SessionLocal() as db:
        await fail_task_in_transaction(
            db, task_id, status, message, diagnostic, worker_token=worker_token,
        )
        await db.commit()


async def complete_text_task(task_id: uuid.UUID, content: str) -> None:
    async with SessionLocal() as db:
        task = await db.scalar(
            select(GenerationTask).where(GenerationTask.id == task_id).with_for_update()
        )
        if not task or task.status in TERMINAL_TASK_STATUSES:
            return
        _transition(task, "succeeded", "text_complete", progress=100)
        task.result = {"type": "text", "content": content}
        task.finished_at = datetime.now(UTC)
        await settle_task_credits(db, task)
        await db.commit()


async def cancel_task(task_id: uuid.UUID, message: str = "任务已取消") -> None:
    await fail_task(task_id, "cancelled", message)


async def resolve_review_task(
    db: AsyncSession, task_id: uuid.UUID, action: str, provider_task_id: str | None = None,
) -> GenerationTask:
    from app.core.errors import ConflictError, NotFoundError, RequestError

    task = await lock_task(db, task_id)
    if not task:
        raise NotFoundError("生成任务不存在")
    if task.status != "needs_review":
        raise ConflictError("任务不是待核查状态")
    if action == "resume":
        if task.task_type == "audio" and (
            provider_task_id or task.provider_task_id or not task.provider_response
        ):
            raise RequestError("同步音频只能恢复已保存的生成结果，无法通过上游任务 ID 恢复")
        if provider_task_id:
            if task.provider_task_id and task.provider_task_id != provider_task_id:
                raise ConflictError("不能替换任务已有的上游任务 ID")
            existing = await db.scalar(
                select(GenerationTask.id).where(
                    GenerationTask.provider == task.provider,
                    GenerationTask.task_type == task.task_type,
                    GenerationTask.provider_task_id == provider_task_id,
                    GenerationTask.id != task.id,
                )
            )
            if existing:
                raise ConflictError("上游任务 ID 已关联其他生成任务")
            task.provider_task_id = provider_task_id
        if task.task_type not in {"image", "video", "audio"}:
            raise RequestError("流式文本任务无法恢复，请取消后重新创建")
        _transition(task, "queued", "admin_review", manual=True)
        task.retry_count += 1
        task.recovery_attempts = 0
        task.error_message = None
        task.diagnostic_snapshot = None
    elif action in {"fail", "cancel"}:
        await fail_task_in_transaction(
            db, task.id, "failed" if action == "fail" else "cancelled",
            "人工核查结束", source="admin_review", manual=True,
        )
    else:
        raise RequestError("未知的待核查处理动作")
    return task
