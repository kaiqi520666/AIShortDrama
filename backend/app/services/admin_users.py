import asyncio
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.errors import NotFoundError, RequestError
from app.models import User
from app.schemas.admin import (
    AdminResetPasswordRequest,
    CreditAdjustmentRequest,
    UserRoleRequest,
    UserStatusRequest,
)
from app.services.admin import (
    active_admin_count,
    add_audit,
    adjust_credits,
    user_snapshot,
)


async def list_users(
    db: AsyncSession, *, q: str, status: str, role: str, page: int, page_size: int
) -> tuple[int, list[User]]:
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
            select(User).where(*filters).order_by(User.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
    )
    return total, users


async def get_target_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.scalar(
        select(User).where(User.id == user_id, User.is_system.is_(False)).with_for_update()
    )
    if not user:
        raise NotFoundError("用户不存在")
    return user


async def adjust_user_credits(
    db: AsyncSession,
    *,
    admin: User,
    user_id: uuid.UUID,
    payload: CreditAdjustmentRequest,
) -> User:
    try:
        return await adjust_credits(
            db, admin=admin, user_id=user_id, amount=payload.amount, reason=payload.reason
        )
    except ValueError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc


async def change_user_role(
    db: AsyncSession,
    *,
    admin: User,
    user_id: uuid.UUID,
    payload: UserRoleRequest,
) -> User:
    user = await get_target_user(db, user_id)
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
    return user


async def change_user_status(
    db: AsyncSession,
    *,
    admin: User,
    user_id: uuid.UUID,
    payload: UserStatusRequest,
) -> User:
    user = await get_target_user(db, user_id)
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
    return user


async def reset_user_password(
    db: AsyncSession,
    *,
    admin: User,
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
) -> User:
    user = await get_target_user(db, user_id)
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
    await db.refresh(user)
    return user
