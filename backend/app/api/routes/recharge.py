import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import NotFoundError, RequestError, ServiceUnavailableError
from app.core.identity import get_current_user
from app.models import RechargeOrder, RechargeTier, User
from app.schemas.recharge import CreateRechargeOrderRequest
from app.schemas.response import success
from app.services.recharge import (
    RechargeError,
    create_order,
    order_data,
    process_notification,
    tier_data,
)
from app.services.admin_configuration import get_billing_policy, policy_data

router = APIRouter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    real_ip = request.headers.get("x-real-ip")
    return real_ip.strip() if real_ip else request.client.host if request.client else "127.0.0.1"


@router.get("/config")
async def get_recharge_config(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    tiers = list(
        await db.scalars(
            select(RechargeTier)
            .where(RechargeTier.enabled.is_(True))
            .order_by(RechargeTier.min_amount_cents)
        )
    )
    policy = await get_billing_policy(db)
    return success(
        {
            **policy_data(policy),
            "min_amount_cents": policy.recharge_min_cents,
            "max_amount_cents": policy.recharge_max_cents,
            "tiers": [tier_data(tier) for tier in tiers],
        }
    )


@router.post("/orders")
async def create_recharge_order(
    payload: CreateRechargeOrderRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        order = await create_order(db, user, payload.amount_cents, _client_ip(request))
    except RechargeError as exc:
        error_type = ServiceUnavailableError if exc.status_code == 503 else RequestError
        raise error_type(str(exc)) from exc
    return success(order_data(order, user.credit_balance))


@router.get("/orders/{order_id}")
async def get_recharge_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await db.scalar(
        select(RechargeOrder).where(
            RechargeOrder.id == order_id, RechargeOrder.user_id == user.id
        )
    )
    if not order:
        raise NotFoundError("充值订单不存在")
    await db.refresh(user)
    return success(order_data(order, user.credit_balance))


@router.get("/zpay/notify", response_class=PlainTextResponse)
async def zpay_notify(request: Request, db: AsyncSession = Depends(get_db)):
    return PlainTextResponse(await process_notification(db, dict(request.query_params)))


@router.get("/zpay/return")
async def zpay_return(request: Request):
    target = f"{get_settings().frontend_base_url.rstrip('/')}/dashboard/recharge"
    order_id = request.query_params.get("param")
    try:
        uuid.UUID(order_id or "")
    except ValueError:
        order_id = None
    if order_id:
        target = f"{target}?{urlencode({'order': order_id})}"
    return RedirectResponse(target)
