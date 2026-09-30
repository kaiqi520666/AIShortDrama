import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, RequestError, ServiceUnavailableError
from app.core.identity import get_current_admin
from app.models import GenerationTask, User
from app.schemas.response import success

router = APIRouter()
logger = logging.getLogger(__name__)


def page_data(page: int, page_size: int, total: int, items: list[dict]) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def task_summary_data(task: GenerationTask, user: User) -> dict:
    return {
        "id": str(task.id),
        "user": {"id": str(user.id), "username": user.username, "email": user.email},
        "task_type": task.task_type,
        "provider": task.provider,
        "model": task.model,
        "status": task.status,
        "progress": task.progress,
        "provider_task_id": task.provider_task_id,
        "frozen_credits": task.frozen_credits,
        "charged_credits": task.charged_credits,
        "credit_status": task.credit_status,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def task_detail_data(task: GenerationTask, user: User) -> dict:
    return {
        **task_summary_data(task, user),
        "workspace_id": str(task.workspace_id),
        "node_id": task.node_id,
        "diagnostic_snapshot": task.diagnostic_snapshot,
        "request_snapshot": task.request_snapshot,
        "pricing_snapshot": task.pricing_snapshot,
        "result": task.result,
        "retry_count": task.retry_count,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "updated_at": task.updated_at.isoformat(),
    }


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
    try:
        from app.api.routes import admin as admin_routes

        async with admin_routes.ToApisProvider() as provider:
            fetch = provider.get_image_task if task.task_type == "image" else provider.get_video_task
            state = await fetch(task.provider_task_id)
    except Exception as exc:
        logger.exception("Admin provider status query failed", extra={"task_id": str(task.id)})
        raise ServiceUnavailableError("上游状态查询失败，请稍后重试") from exc
    error = state.get("error") or {}
    error_message = error.get("message") if isinstance(error, dict) else str(error)
    return success({
        "provider_task_id": task.provider_task_id,
        "status": state.get("status") or "unknown",
        "progress": max(0, min(100, int(state.get("progress") or 0))),
        "error_message": str(error_message) if error_message else None,
        "checked_at": datetime.now(UTC).isoformat(),
    })
