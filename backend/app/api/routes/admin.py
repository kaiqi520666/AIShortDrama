import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.database import get_db
from app.core.identity import get_current_admin
from app.models import AdminAuditLog, GenerationTask, ModelPriceRule, User
from app.schemas.admin import (
    AdminResetPasswordRequest,
    CreditAdjustmentRequest,
    PriceRuleUpdateRequest,
    UserRoleRequest,
    UserStatusRequest,
)
from app.schemas.response import success
from app.services.admin import active_admin_count, add_audit, adjust_credits, price_snapshot, user_snapshot

router = APIRouter()


def page_data(page: int, page_size: int, total: int, items: list[dict]) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def user_data(user: User) -> dict:
    return {"id": str(user.id), **user_snapshot(user), "created_at": user.created_at.isoformat()}


def rule_data(rule: ModelPriceRule) -> dict:
    return {"id": str(rule.id), **price_snapshot(rule), "created_at": rule.created_at.isoformat(), "updated_at": rule.updated_at.isoformat()}


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
    users = list(await db.scalars(select(User).where(*filters).order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return success(page_data(page, page_size, total, [user_data(user) for user in users]))


async def target_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.scalar(select(User).where(User.id == user_id, User.is_system.is_(False)).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/users/{user_id}/credits")
async def update_user_credits(
    user_id: uuid.UUID,
    payload: CreditAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        user = await adjust_credits(db, admin=admin, user_id=user_id, amount=payload.amount, reason=payload.reason)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        raise HTTPException(status_code=400, detail="不能降低自己的管理员角色")
    if user.role == "admin" and payload.role != "admin" and user.status == "active" and await active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="至少需要保留一名启用的管理员")
    before = user_snapshot(user)
    if user.role != payload.role:
        user.role = payload.role
        user.auth_version += 1
    add_audit(db, admin_id=admin.id, action="change_role", target_type="user", target_id=user.id, reason=payload.reason, before=before, after=user_snapshot(user))
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
        raise HTTPException(status_code=400, detail="不能停用自己的账号")
    if user.role == "admin" and user.status == "active" and payload.status != "active" and await active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="至少需要保留一名启用的管理员")
    before = user_snapshot(user)
    if user.status != payload.status:
        user.status = payload.status
        user.auth_version += 1
    add_audit(db, admin_id=admin.id, action="change_status", target_type="user", target_id=user.id, reason=payload.reason, before=before, after=user_snapshot(user))
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
    add_audit(db, admin_id=admin.id, action="reset_password", target_type="user", target_id=user.id, reason=payload.reason, before=before, after=user_snapshot(user))
    await db.commit()
    return success(user_data(user))


@router.get("/pricing")
async def list_price_rules(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rules = list(await db.scalars(select(ModelPriceRule).order_by(ModelPriceRule.media_type, ModelPriceRule.model, ModelPriceRule.specification)))
    return success([rule_data(rule) for rule in rules])


@router.put("/pricing/{rule_id}")
async def update_price_rule(
    rule_id: uuid.UUID,
    payload: PriceRuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rule = await db.scalar(select(ModelPriceRule).where(ModelPriceRule.id == rule_id).with_for_update())
    if not rule:
        raise HTTPException(status_code=404, detail="计费规则不存在")
    before = price_snapshot(rule)
    for field, value in payload.model_dump(exclude={"reason"}).items():
        setattr(rule, field, value)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="模型、类型和规格组合已存在") from exc
    add_audit(db, admin_id=admin.id, action="update_pricing", target_type="price_rule", target_id=rule.id, reason=payload.reason, before=before, after=price_snapshot(rule))
    await db.commit()
    await db.refresh(rule)
    return success(rule_data(rule))


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
    items = [{
        "id": str(task.id), "user": {"id": str(user.id), "username": user.username, "email": user.email},
        "task_type": task.task_type, "provider": task.provider, "model": task.model, "status": task.status,
        "progress": task.progress, "frozen_credits": task.frozen_credits, "charged_credits": task.charged_credits,
        "credit_status": task.credit_status, "request_snapshot": task.request_snapshot, "pricing_snapshot": task.pricing_snapshot,
        "result": task.result, "error_message": task.error_message, "created_at": task.created_at.isoformat(),
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    } for task, user in rows]
    return success(page_data(page, page_size, total, items))


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
    statement = select(AdminAuditLog, User).join(User, User.id == AdminAuditLog.admin_id).where(*filters)
    total = int(await db.scalar(select(func.count()).select_from(AdminAuditLog).where(*filters)) or 0)
    rows = (await db.execute(statement.order_by(AdminAuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    items = [{
        "id": str(audit.id), "admin": {"id": str(admin.id), "username": admin.username}, "action": audit.action,
        "target_type": audit.target_type, "target_id": audit.target_id, "reason": audit.reason,
        "before_snapshot": audit.before_snapshot, "after_snapshot": audit.after_snapshot, "created_at": audit.created_at.isoformat(),
    } for audit, admin in rows]
    return success(page_data(page, page_size, total, items))
