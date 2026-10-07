from app.api.routes.admin_presenters import page_data
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
    User,
)
from app.schemas.response import success

router = APIRouter()
logger = logging.getLogger(__name__)


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
