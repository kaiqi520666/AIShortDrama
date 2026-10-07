import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, RequestError, ServiceUnavailableError
from app.models import (
    BillingPolicy,
    CreditPolicy,
    ModelPriceRule,
    RechargeOrder,
    RechargeTier,
    User,
)
from app.schemas.admin import (
    BillingPolicyUpdateRequest,
    CreditPolicyUpdateRequest,
    PriceRuleUpdateRequest,
    RechargeTierMutationRequest,
)
from app.services.admin import add_audit, price_snapshot
from app.services.admin_configuration import (
    credit_policy_data,
    get_billing_policy,
    get_credit_policy,
    policy_data,
)
from app.services.recharge import RechargeError, sync_cahaya_order, tier_data, validate_tiers


async def list_price_rules(db: AsyncSession) -> list[ModelPriceRule]:
    return list(
        await db.scalars(
            select(ModelPriceRule).order_by(
                ModelPriceRule.media_type, ModelPriceRule.model, ModelPriceRule.specification
            )
        )
    )


async def list_recharge_tiers(db: AsyncSession) -> list[RechargeTier]:
    return list(
        await db.scalars(
            select(RechargeTier).order_by(RechargeTier.currency, RechargeTier.min_amount_cents)
        )
    )


async def list_recharge_orders(
    db: AsyncSession,
    *,
    q: str,
    status: str,
    start_at: datetime | None,
    end_at: datetime | None,
    page: int,
    page_size: int,
):
    filters = []
    if q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(
            User.username.ilike(term),
            User.email.ilike(term),
            RechargeOrder.out_trade_no.ilike(term),
            RechargeOrder.provider_trade_no.ilike(term),
        ))
    if status != "all":
        filters.append(RechargeOrder.status == status)
    if start_at:
        filters.append(RechargeOrder.created_at >= start_at)
    if end_at:
        filters.append(RechargeOrder.created_at < end_at)
    statement = (
        select(RechargeOrder, User).join(User, User.id == RechargeOrder.user_id).where(*filters)
    )
    total = int(
        await db.scalar(select(func.count()).select_from(RechargeOrder).join(User).where(*filters))
        or 0
    )
    rows = (
        await db.execute(
            statement.order_by(RechargeOrder.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return total, rows


async def get_recharge_order(db: AsyncSession, order_id: uuid.UUID) -> RechargeOrder:
    order = await db.get(RechargeOrder, order_id)
    if not order:
        raise NotFoundError("充值订单不存在")
    return order


async def refresh_recharge_order(db: AsyncSession, order_id: uuid.UUID) -> RechargeOrder:
    order = await get_recharge_order(db, order_id)
    try:
        if order.provider == "cahaya":
            order = await sync_cahaya_order(db, order)
    except RechargeError as exc:
        error_type = ServiceUnavailableError if exc.status_code == 503 else RequestError
        raise error_type(str(exc)) from exc
    return order


async def update_price_rule(
    db: AsyncSession,
    *,
    admin: User,
    rule_id: uuid.UUID,
    payload: PriceRuleUpdateRequest,
) -> ModelPriceRule:
    rule = await db.scalar(
        select(ModelPriceRule).where(ModelPriceRule.id == rule_id).with_for_update()
    )
    if not rule:
        raise NotFoundError("计费规则不存在")
    before = price_snapshot(rule)
    for field, value in payload.model_dump(exclude={"reason"}).items():
        setattr(rule, field, value)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise RequestError("模型、类型和规格组合已存在") from exc
    add_audit(
        db,
        admin_id=admin.id,
        action="update_pricing",
        target_type="price_rule",
        target_id=rule.id,
        reason=payload.reason,
        before=before,
        after=price_snapshot(rule),
    )
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_billing_policy(
    db: AsyncSession,
    *,
    admin: User,
    payload: BillingPolicyUpdateRequest,
) -> BillingPolicy:
    policy = await get_billing_policy(db, lock=True)
    tiers = list(await db.scalars(select(RechargeTier).with_for_update()))
    before = policy_data(policy)
    for field, value in payload.model_dump(exclude={"reason"}, exclude_none=True).items():
        setattr(policy, field, value)
    try:
        validate_tiers(tiers, policy)
    except RechargeError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc
    policy.version += 1
    add_audit(
        db,
        admin_id=admin.id,
        action="update_billing_policy",
        target_type="billing_policy",
        target_id=policy.key,
        reason=payload.reason,
        before=before,
        after=policy_data(policy),
    )
    await db.commit()
    await db.refresh(policy)
    return policy


async def update_credit_policy(
    db: AsyncSession,
    *,
    admin: User,
    payload: CreditPolicyUpdateRequest,
) -> CreditPolicy:
    policy = await get_credit_policy(db, lock=True)
    before = credit_policy_data(policy)
    for field, value in payload.model_dump(exclude={"reason"}).items():
        setattr(policy, field, value)
    policy.version += 1
    add_audit(
        db,
        admin_id=admin.id,
        action="update_credit_policy",
        target_type="credit_policy",
        target_id=policy.key,
        reason=payload.reason,
        before=before,
        after=credit_policy_data(policy),
    )
    await db.commit()
    await db.refresh(policy)
    return policy


async def create_recharge_tier(
    db: AsyncSession,
    *,
    admin: User,
    payload: RechargeTierMutationRequest,
) -> RechargeTier:
    tiers = list(await db.scalars(select(RechargeTier).with_for_update()))
    if any(
        tier.currency == payload.currency and tier.min_amount_cents == payload.min_amount_cents
        for tier in tiers
    ):
        raise RequestError("该充值金额阶梯已存在")
    tier = RechargeTier(**payload.model_dump(exclude={"reason"}))
    try:
        validate_tiers([*tiers, tier], await get_billing_policy(db))
    except RechargeError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc
    db.add(tier)
    await db.flush()
    add_audit(
        db,
        admin_id=admin.id,
        action="create_recharge_tier",
        target_type="recharge_tier",
        target_id=tier.id,
        reason=payload.reason,
        before={},
        after=tier_data(tier),
    )
    await db.commit()
    await db.refresh(tier)
    return tier


async def update_recharge_tier(
    db: AsyncSession,
    *,
    admin: User,
    tier_id: uuid.UUID,
    payload: RechargeTierMutationRequest,
) -> RechargeTier:
    tiers = list(await db.scalars(select(RechargeTier).with_for_update()))
    tier = next((item for item in tiers if item.id == tier_id), None)
    if not tier:
        raise NotFoundError("充值阶梯不存在")
    if any(
        item.id != tier_id
        and item.currency == payload.currency
        and item.min_amount_cents == payload.min_amount_cents
        for item in tiers
    ):
        raise RequestError("该充值金额阶梯已存在")
    before = tier_data(tier)
    tier.currency = payload.currency
    tier.min_amount_cents = payload.min_amount_cents
    tier.bonus_rate_bps = payload.bonus_rate_bps
    tier.enabled = payload.enabled
    try:
        validate_tiers(tiers, await get_billing_policy(db))
    except RechargeError as exc:
        await db.rollback()
        raise RequestError(str(exc)) from exc
    add_audit(
        db,
        admin_id=admin.id,
        action="update_recharge_tier",
        target_type="recharge_tier",
        target_id=tier.id,
        reason=payload.reason,
        before=before,
        after=tier_data(tier),
    )
    await db.commit()
    await db.refresh(tier)
    return tier
