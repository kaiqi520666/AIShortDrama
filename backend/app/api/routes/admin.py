import logging
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import (
    RequestError,
)
from app.core.identity import get_current_admin
from app.models import (
    CreditLedger,
    GenerationTask,
    RechargeOrder,
    User,
)
from app.schemas.response import success

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def get_admin_dashboard(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    if days not in {1, 7, 30}:
        raise RequestError("统计周期仅支持 1、7 或 30 天")
    start_at = datetime.now(UTC) - timedelta(days=days)
    recharge_amount = int(
        await db.scalar(
            select(func.coalesce(func.sum(RechargeOrder.amount_cents), 0)).where(
                RechargeOrder.status == "paid", RechargeOrder.created_at >= start_at
            )
        )
        or 0
    )
    recharge_orders = int(
        await db.scalar(
            select(func.count())
            .select_from(RechargeOrder)
            .where(RechargeOrder.status == "paid", RechargeOrder.created_at >= start_at)
        )
        or 0
    )
    consumed_credits = int(
        await db.scalar(
            select(func.coalesce(func.sum(CreditLedger.amount), 0)).where(
                CreditLedger.entry_type == "consume", CreditLedger.created_at >= start_at
            )
        )
        or 0
    )
    status_rows = (
        await db.execute(
            select(GenerationTask.status, func.count())
            .where(GenerationTask.created_at >= start_at)
            .group_by(GenerationTask.status)
        )
    ).all()
    status_counts = {status: int(count) for status, count in status_rows}
    model_rows = (
        await db.execute(
            select(GenerationTask.model, func.count())
            .where(GenerationTask.created_at >= start_at)
            .group_by(GenerationTask.model)
            .order_by(func.count().desc(), GenerationTask.model)
        )
    ).all()
    terminal = sum(
        status_counts.get(status, 0) for status in ("succeeded", "failed", "timeout", "cancelled")
    )
    succeeded = status_counts.get("succeeded", 0)
    queued_tasks = int(
        await db.scalar(
            select(func.count())
            .select_from(GenerationTask)
            .where(GenerationTask.status == "queued")
        )
        or 0
    )
    running_tasks = int(
        await db.scalar(
            select(func.count())
            .select_from(GenerationTask)
            .where(GenerationTask.status == "running")
        )
        or 0
    )
    needs_review_tasks = int(
        await db.scalar(
            select(func.count())
            .select_from(GenerationTask)
            .where(GenerationTask.status == "needs_review")
        )
        or 0
    )
    stale_cutoff = datetime.now(UTC) - timedelta(minutes=30)
    stale_tasks = int(
        await db.scalar(
            select(func.count())
            .select_from(GenerationTask)
            .where(
                GenerationTask.credit_status == "frozen",
                (
                    (GenerationTask.status == "queued")
                    & (GenerationTask.created_at < stale_cutoff)
                )
                | (
                    (GenerationTask.status == "running")
                    & (GenerationTask.updated_at < stale_cutoff)
                ),
            )
        )
        or 0
    )
    queue_depth = None
    try:
        from app.core.config import get_settings

        queue_depth = int(await request.app.state.redis.zcard(get_settings().redis_queue_name))
    except Exception:
        queue_depth = None
    return success(
        {
            "days": days,
            "recharge_amount_cents": recharge_amount,
            "recharge_order_count": recharge_orders,
            "consumed_credits": consumed_credits,
            "task_count": sum(status_counts.values()),
            "succeeded_count": succeeded,
            "failed_count": status_counts.get("failed", 0),
            "timeout_count": status_counts.get("timeout", 0),
            "success_rate": round(succeeded / terminal, 4) if terminal else None,
            "queued_task_count": queued_tasks,
            "running_task_count": running_tasks,
            "needs_review_task_count": needs_review_tasks,
            "stale_task_count": stale_tasks,
            "queue_depth": queue_depth,
            "model_calls": [{"model": model, "count": int(count)} for model, count in model_rows],
        }
    )
