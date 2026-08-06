import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import CreditLedger, RechargeOrder, RechargeTier, User
from app.providers.zpay import sign_params
from app.services import recharge as recharge_service
from app.services.recharge import RechargeError, calculate_recharge, process_notification, validate_tiers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("amount_cents", "base", "bonus"),
    [
        (3500, 1000, 0),
        (10400, 2971, 0),
        (10500, 3000, 90),
        (17500, 5000, 300),
        (35000, 10000, 800),
        (70000, 20000, 2000),
    ],
)
async def test_recharge_quotes_use_highest_enabled_tier(amount_cents, base, bonus):
    async with SessionLocal() as db:
        quote = await calculate_recharge(db, amount_cents)
        assert quote.base_credits == base
        assert quote.bonus_credits == bonus


def test_recharge_tier_validation_requires_coverage_and_increasing_bonus():
    valid = [
        SimpleNamespace(min_amount_cents=3500, bonus_rate_bps=0, enabled=True),
        SimpleNamespace(min_amount_cents=10500, bonus_rate_bps=300, enabled=True),
    ]
    validate_tiers(valid)
    with pytest.raises(RechargeError, match="35 元"):
        validate_tiers(valid[1:])
    valid[1].bonus_rate_bps = -1
    with pytest.raises(RechargeError, match="不能降低"):
        validate_tiers(valid)


@pytest.mark.asyncio
async def test_zpay_notification_credits_user_once(monkeypatch, override_business_user):
    order_id = uuid.uuid4()
    before = 0
    async with SessionLocal() as db:
        user = await db.get(User, override_business_user)
        before = user.credit_balance
        tier = await db.scalar(
            select(RechargeTier).where(RechargeTier.min_amount_cents == 3500)
        )
        db.add(
            RechargeOrder(
                id=order_id,
                user_id=user.id,
                tier_id=tier.id,
                out_trade_no=f"test{order_id.hex[:20]}",
                amount_cents=3500,
                base_credits=1000,
                bonus_credits=0,
                total_credits=1000,
                tier_snapshot={"bonus_rate_bps": 0},
            )
        )
        await db.commit()

    settings = SimpleNamespace(zpay_key="secret", zpay_pid="merchant-1")
    monkeypatch.setattr(recharge_service, "get_settings", lambda: settings)
    params = {
        "pid": "merchant-1",
        "trade_status": "TRADE_SUCCESS",
        "out_trade_no": f"test{order_id.hex[:20]}",
        "trade_no": "provider-1",
        "money": "35.00",
        "sign_type": "MD5",
    }
    params["sign"] = sign_params(params, "secret")

    async with SessionLocal() as db:
        assert await process_notification(db, params) == "success"
    async with SessionLocal() as db:
        assert await process_notification(db, params) == "success"
    async with SessionLocal() as db:
        user = await db.get(User, override_business_user)
        order = await db.get(RechargeOrder, order_id)
        ledgers = list(
            await db.scalars(
                select(CreditLedger).where(CreditLedger.recharge_order_id == order_id)
            )
        )
        assert user.credit_balance == before + 1000
        assert order.status == "paid"
        assert len(ledgers) == 1
