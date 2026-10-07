from app.api.routes.admin_presenters import page_data, task_detail_data, task_summary_data
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, RequestError, ServiceUnavailableError
from app.core.identity import get_current_admin
from app.models import GenerationTask, User
from app.providers.registry import create_generation_provider
from app.schemas.admin import ResolveReviewRequest
from app.schemas.response import success
from app.services.admin import add_audit
from app.services.task_lifecycle import lock_task, resolve_review_task

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tasks")
async def list_tasks(
    q: str = "",
    media_type: str = Query("all", pattern="^(all|text|image|video|audio)$"),
    model: str = "",
    status: str = "",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    filters = []
    if q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(User.username.ilike(term), User.email.ilike(term)))
    if media_type != "all":
        filters.append(GenerationTask.task_type.in_([media_type, f"{media_type}_reverse"]))
    if model.strip():
        filters.append(GenerationTask.model == model.strip())
    if status.strip():
        filters.append(GenerationTask.status == status.strip())
    if start_at:
        filters.append(GenerationTask.created_at >= start_at)
    if end_at:
        filters.append(GenerationTask.created_at < end_at)
    statement = select(GenerationTask, User).join(User, User.id == GenerationTask.user_id).where(*filters)
    total = int(await db.scalar(select(func.count()).select_from(GenerationTask).join(User).where(*filters)) or 0)
    rows = (await db.execute(statement.order_by(GenerationTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return success(page_data(page, page_size, total, [task_summary_data(task, user) for task, user in rows]))


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    row = (
        await db.execute(
            select(GenerationTask, User)
            .join(User, User.id == GenerationTask.user_id)
            .where(GenerationTask.id == task_id)
        )
    ).one_or_none()
    if not row:
        raise NotFoundError("生成任务不存在")
    return success(task_detail_data(*row))


@router.post("/tasks/{task_id}/provider-status")
async def get_task_provider_status(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise NotFoundError("生成任务不存在")
    if not task.provider_task_id:
        raise RequestError("该任务没有 Provider 任务 ID，无法查询上游状态")
    if task.provider != "toapis" or task.task_type not in {"image", "video"}:
        raise RequestError("该任务暂不支持查询上游状态")
    provider = None
    try:
        provider = create_generation_provider(task.provider, task.task_type)
        state = await provider.get_task(task.provider_task_id)
    except Exception as exc:
        logger.exception("Admin provider status query failed", extra={"task_id": str(task.id)})
        raise ServiceUnavailableError("上游状态查询失败，请稍后重试") from exc
    finally:
        if provider is not None:
            await provider.aclose()
    error = state.get("error") or {}
    error_message = error.get("message") if isinstance(error, dict) else str(error)
    return success({
        "provider_task_id": task.provider_task_id,
        "status": state.get("status") or "unknown",
        "progress": max(0, min(100, int(state.get("progress") or 0))),
        "error_message": str(error_message) if error_message else None,
        "checked_at": datetime.now(UTC).isoformat(),
    })


@router.post("/tasks/{task_id}/resolve-review")
async def resolve_task_review(
    task_id: uuid.UUID,
    payload: ResolveReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if payload.action != "resume" and payload.provider_task_id:
        raise RequestError("只有恢复任务时才能指定 Provider 任务 ID")
    existing = await lock_task(db, task_id)
    if existing is None:
        raise NotFoundError("生成任务不存在")
    before = {
        "status": existing.status,
        "provider_task_id": existing.provider_task_id,
        "credit_status": existing.credit_status,
    }
    task = await resolve_review_task(
        db, task_id, payload.action, provider_task_id=payload.provider_task_id
    )
    add_audit(
        db,
        admin_id=admin.id,
        action=f"resolve_task_review_{payload.action}",
        target_type="generation_task",
        target_id=task.id,
        reason=payload.reason,
        before=before,
        after={
            "status": task.status,
            "provider_task_id": task.provider_task_id,
            "credit_status": task.credit_status,
        },
    )
    await db.commit()
    await db.refresh(task)
    if payload.action == "resume":
        try:
            await request.app.state.redis.enqueue_job(
                f"generate_{task.task_type}",
                str(task.id),
                _job_id=f"generation:{task.id}:review:{task.retry_count}",
            )
        except Exception as exc:
            logger.exception(
                "Failed to enqueue manually resumed task",
                extra={"task_id": str(task.id)},
            )
            raise ServiceUnavailableError("任务已恢复，但重新入队失败") from exc
    owner = await db.get(User, task.user_id)
    return success(task_detail_data(task, owner or admin))
