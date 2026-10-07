import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin_presenters import page_data, user_data
from app.core.database import get_db
from app.core.identity import get_current_admin
from app.models import User
from app.schemas.admin import (
    AdminResetPasswordRequest,
    CreditAdjustmentRequest,
    UserRoleRequest,
    UserStatusRequest,
)
from app.schemas.response import success
from app.services.admin_users import (
    adjust_user_credits,
    change_user_role,
    change_user_status,
    list_users as list_admin_users,
    reset_user_password as reset_password,
)

router = APIRouter()


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
    total, users = await list_admin_users(
        db, q=q, status=status, role=role, page=page, page_size=page_size
    )
    return success(page_data(page, page_size, total, [user_data(user) for user in users]))


@router.post("/users/{user_id}/credits")
async def update_user_credits(
    user_id: uuid.UUID,
    payload: CreditAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await adjust_user_credits(db, admin=admin, user_id=user_id, payload=payload)
    return success(user_data(user))


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await change_user_role(db, admin=admin, user_id=user_id, payload=payload)
    return success(user_data(user))


@router.post("/users/{user_id}/status")
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await change_user_status(db, admin=admin, user_id=user_id, payload=payload)
    return success(user_data(user))


@router.post("/users/{user_id}/password")
async def reset_user_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await reset_password(db, admin=admin, user_id=user_id, payload=payload)
    return success(user_data(user))
