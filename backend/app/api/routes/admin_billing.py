import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin_presenters import page_data, rule_data
from app.core.database import get_db
from app.core.identity import get_current_admin
from app.models import User
from app.schemas.admin import (
    BillingPolicyUpdateRequest,
    CreditPolicyUpdateRequest,
    PriceRuleUpdateRequest,
    RechargeTierMutationRequest,
)
from app.schemas.response import success
from app.services import admin_billing as billing_service
from app.services.admin_configuration import (
    credit_policy_data,
    get_billing_policy,
    get_credit_policy,
    policy_data,
)
from app.services.recharge import (
    admin_order_data,
    order_data,
    tier_data,
)

router = APIRouter()


@router.get("/pricing")
async def list_price_rules(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rules = await billing_service.list_price_rules(db)
    return success([rule_data(rule) for rule in rules])


@router.put("/pricing/{rule_id}")
async def update_price_rule(
    rule_id: uuid.UUID,
    payload: PriceRuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rule = await billing_service.update_price_rule(
        db, admin=admin, rule_id=rule_id, payload=payload
    )
    return success(rule_data(rule))


@router.get("/billing-policy")
async def get_billing_policy_data(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return success(policy_data(await get_billing_policy(db)))


@router.put("/billing-policy")
async def update_billing_policy(
    payload: BillingPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    policy = await billing_service.update_billing_policy(db, admin=admin, payload=payload)
    return success(policy_data(policy))


@router.get("/credit-policy")
async def get_credit_policy_data(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return success(credit_policy_data(await get_credit_policy(db)))


@router.put("/credit-policy")
async def update_credit_policy(
    payload: CreditPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    policy = await billing_service.update_credit_policy(db, admin=admin, payload=payload)
    return success(credit_policy_data(policy))


@router.get("/recharge/tiers")
async def list_recharge_tiers(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    tiers = await billing_service.list_recharge_tiers(db)
    return success([tier_data(tier) for tier in tiers])


@router.post("/recharge/tiers")
async def create_recharge_tier(
    payload: RechargeTierMutationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    tier = await billing_service.create_recharge_tier(db, admin=admin, payload=payload)
    return success(tier_data(tier))


@router.put("/recharge/tiers/{tier_id}")
async def update_recharge_tier(
    tier_id: uuid.UUID,
    payload: RechargeTierMutationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    tier = await billing_service.update_recharge_tier(
        db, admin=admin, tier_id=tier_id, payload=payload
    )
    return success(tier_data(tier))


@router.get("/recharge/orders")
async def list_recharge_orders(
    q: str = "",
    status: str = Query("all", pattern="^(all|pending|paid|failed)$"),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    total, rows = await billing_service.list_recharge_orders(
        db, q=q, status=status, start_at=start_at, end_at=end_at,
        page=page, page_size=page_size,
    )
    items = [
        {
            **order_data(order),
            "user": {"id": str(user.id), "username": user.username, "email": user.email},
        }
        for order, user in rows
    ]
    return success(page_data(page, page_size, total, items))


@router.get("/recharge/orders/{order_id}")
async def get_admin_recharge_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    order = await billing_service.get_recharge_order(db, order_id)
    return success(admin_order_data(order))


@router.post("/recharge/orders/{order_id}/query")
async def query_admin_recharge_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    order = await billing_service.refresh_recharge_order(db, order_id)
    return success(admin_order_data(order))
