import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_admin
from app.models import (
    AdminAuditLog,
    GenerationTask,
    ModelPriceRule,
    User,
)
from app.schemas.response import success
from app.services.admin import price_snapshot, user_snapshot

router = APIRouter()
logger = logging.getLogger(__name__)


def page_data(page: int, page_size: int, total: int, items: list[dict]) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def user_data(user: User) -> dict:
    return {"id": str(user.id), **user_snapshot(user), "created_at": user.created_at.isoformat()}


def rule_data(rule: ModelPriceRule) -> dict:
    return {
        "id": str(rule.id),
        **price_snapshot(rule),
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


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


@router.get("/audits")
async def list_audits(
    admin_id: uuid.UUID | None = None,
    action: str = "",
    target_type: str = "",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    filters = []
    if admin_id:
        filters.append(AdminAuditLog.admin_id == admin_id)
    if action.strip():
        filters.append(AdminAuditLog.action == action.strip())
    if target_type.strip():
        filters.append(AdminAuditLog.target_type == target_type.strip())
    if start_at:
        filters.append(AdminAuditLog.created_at >= start_at)
    if end_at:
        filters.append(AdminAuditLog.created_at < end_at)
    statement = (
        select(AdminAuditLog, User).join(User, User.id == AdminAuditLog.admin_id).where(*filters)
    )
    total = int(
        await db.scalar(select(func.count()).select_from(AdminAuditLog).where(*filters)) or 0
    )
    rows = (
        await db.execute(
            statement.order_by(AdminAuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [
        {
            "id": str(audit.id),
            "admin": {"id": str(admin.id), "username": admin.username},
            "action": audit.action,
            "target_type": audit.target_type,
            "target_id": audit.target_id,
            "reason": audit.reason,
            "before_snapshot": audit.before_snapshot,
            "after_snapshot": audit.after_snapshot,
            "created_at": audit.created_at.isoformat(),
        }
        for audit, admin in rows
    ]
    return success(page_data(page, page_size, total, items))
