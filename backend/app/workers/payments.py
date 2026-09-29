import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import RechargeOrder
from app.services.recharge import RechargeError, sync_cahaya_order

logger = logging.getLogger(__name__)


async def reconcile_cahaya_orders(_ctx) -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    async with SessionLocal() as db:
        orders = list(await db.scalars(
            select(RechargeOrder)
            .where(
                RechargeOrder.provider == "cahaya",
                RechargeOrder.status == "pending",
                RechargeOrder.created_at < cutoff,
            )
            .order_by(RechargeOrder.created_at)
            .limit(20)
        ))
        for order in orders:
            try:
                await sync_cahaya_order(db, order)
            except RechargeError:
                logger.warning("Cahaya order reconciliation failed", extra={"order_id": str(order.id)}, exc_info=True)
