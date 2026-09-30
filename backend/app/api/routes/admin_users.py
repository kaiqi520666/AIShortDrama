import asyncio
import logging
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.database import get_db
from app.core.errors import (
    NotFoundError,
    RequestError,
)
from app.core.identity import get_current_admin
from app.models import (
    GenerationTask,
    ModelPriceRule,
    User,
)
from app.schemas.admin import (
    AdminResetPasswordRequest,
    CreditAdjustmentRequest,
    UserRoleRequest,
    UserStatusRequest,
)
from app.schemas.response import success
from app.services.admin import (
    active_admin_count,
    add_audit,
    adjust_credits,
    price_snapshot,
    user_snapshot,
)

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


@router.get("/users")
async def list_users(
    q: str = "",
    status: str = Query("all", pattern="^(all|active|disabled)$"),
    role: str = Query("all", pattern="^(all|user|admin)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    filters = [User.is_system.is_(False)]
    if q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(User.username.ilike(term), User.email.ilike(term)))
    if status != "all":
        filters.append(User.status == status)
    if role != "all":
        filters.append(User.role == role)
    total = int(await db.scalar(select(func.count()).select_from(User).where(*filters)) or 0)
    users = list(
        await db.scalars(
            select(User)
            .where(*filters)
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return success(page_data(page, page_size, total, [user_data(user) for user in users]))


async def target_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.scalar(
        select(User).where(User.id == user_id, User.is_system.is_(False)).with_for_update()
    )
    if not user:
        raise NotFoundError("用户不存在")
    return user


@router.post("/users/{user_id}/credits")
async def update_user_credits(
    user_id: uuid.UUID,
    payload: CreditAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        user = await adjust_credits(
            db, admin=admin, user_id=user_id, amount=payload.amount, reason=payload.reason
        )
    except ValueError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc
    return success(user_data(user))


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await target_user(db, user_id)
    if user.id == admin.id and payload.role != "admin":
        raise RequestError("不能降低自己的管理员角色")
    if (
        user.role == "admin"
        and payload.role != "admin"
        and user.status == "active"
        and await active_admin_count(db) <= 1
    ):
        raise RequestError("至少需要保留一名启用的管理员")
    before = user_snapshot(user)
    if user.role != payload.role:
        user.role = payload.role
        user.auth_version += 1
    add_audit(
        db,
        admin_id=admin.id,
        action="change_role",
        target_type="user",
        target_id=user.id,
        reason=payload.reason,
        before=before,
        after=user_snapshot(user),
    )
    await db.commit()
    await db.refresh(user)
    return success(user_data(user))


@router.post("/users/{user_id}/status")
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await target_user(db, user_id)
    if user.id == admin.id and payload.status != "active":
        raise RequestError("不能停用自己的账号")
    if (
        user.role == "admin"
        and user.status == "active"
        and payload.status != "active"
        and await active_admin_count(db) <= 1
    ):
        raise RequestError("至少需要保留一名启用的管理员")
    before = user_snapshot(user)
    if user.status != payload.status:
        user.status = payload.status
        user.auth_version += 1
    add_audit(
        db,
        admin_id=admin.id,
        action="change_status",
        target_type="user",
        target_id=user.id,
        reason=payload.reason,
        before=before,
        after=user_snapshot(user),
    )
    await db.commit()
    await db.refresh(user)
    return success(user_data(user))


@router.post("/users/{user_id}/password")
async def reset_user_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await target_user(db, user_id)
    before = user_snapshot(user)
    user.password_hash = await asyncio.to_thread(hash_password, payload.new_password)
    user.auth_version += 1
    add_audit(
        db,
        admin_id=admin.id,
        action="reset_password",
        target_type="user",
        target_id=user.id,
        reason=payload.reason,
        before=before,
        after=user_snapshot(user),
    )
    await db.commit()
    return success(user_data(user))
