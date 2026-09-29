import uuid
import json
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import CreditLedger, RechargeOrder, RechargeTier, User
from app.providers import cahaya as cahaya_provider
from app.providers.zpay import sign_params
from app.providers.cahaya import sign_payload, verify_payload
from app.services import recharge as recharge_service
from app.services.recharge import RechargeError, calculate_recharge, process_cahaya_notification, process_notification, validate_tiers


def test_cahaya_signature_uses_sorted_public_fields_and_access_token_last():
    payload = {"terminal_no": "10005965", "req_ver": "1.0", "req_mode": "1", "req_time": "1772701701326", "req_id": "367799fe-e909-45b7-a91a-917c43cd8941", "req_params": '{"pay_type":"2"}'}
    signature = sign_payload(payload, "31cf7844f0ae4360adea6ca1a280f6ae")
    assert len(signature) == 32
    assert verify_payload({**payload, "key_sign": signature}, "31cf7844f0ae4360adea6ca1a280f6ae")
    assert not verify_payload({**payload, "key_sign": "wrong"}, "31cf7844f0ae4360adea6ca1a280f6ae")


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


def test_cahaya_terminal_ip_requires_public_ipv4(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "development")
    assert recharge_service._cahaya_terminal_ip("8.8.8.8") == "8.8.8.8"
    assert recharge_service._cahaya_terminal_ip("127.0.0.1") == "8.8.8.8"
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(RechargeError, match="公网"):
        recharge_service._cahaya_terminal_ip("127.0.0.1")


def test_recharge_tier_validation_requires_coverage_and_increasing_bonus():
    policy = SimpleNamespace(recharge_min_cents=3500)
    valid = [
        SimpleNamespace(min_amount_cents=3500, bonus_rate_bps=0, enabled=True),
        SimpleNamespace(min_amount_cents=10500, bonus_rate_bps=300, enabled=True),
    ]
    validate_tiers(valid, policy)
    with pytest.raises(RechargeError, match="35 元"):
        validate_tiers(valid[1:], policy)
    valid[1].bonus_rate_bps = -1
    with pytest.raises(RechargeError, match="不能降低"):
        validate_tiers(valid, policy)


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


@pytest.mark.asyncio
async def test_cahaya_notification_validates_snapshot_and_credits_once(monkeypatch, override_business_user):
    order_id = uuid.uuid4()
    out_trade_no = f"cahaya{order_id.hex[:19]}"
    async with SessionLocal() as db:
        user = await db.get(User, override_business_user)
        tier = await db.scalar(
            select(RechargeTier).where(
                RechargeTier.currency == "IDR",
                RechargeTier.min_amount_cents == 150000,
            )
        )
        db.add(
            RechargeOrder(
                id=order_id,
                user_id=user.id,
                tier_id=tier.id,
                out_trade_no=out_trade_no,
                provider="cahaya",
                amount_cents=0,
                currency="IDR",
                amount_minor=150000,
                base_credits=1000,
                bonus_credits=0,
                total_credits=1000,
                tier_snapshot={"bonus_rate_bps": 0, "currency": "IDR"},
            )
        )
        await db.commit()

    settings = SimpleNamespace(
        cahaya_enabled=False,
        cahaya_merchant_no="merchant-id",
        cahaya_terminal_no="terminal-id",
        cahaya_access_token="access-token",
        cahaya_notify_url="https://mooncut.nodepass.net/api/recharge/cahaya/notify",
        cahaya_timeout_seconds=20,
    )
    monkeypatch.setattr(recharge_service, "get_settings", lambda: settings)
    monkeypatch.setattr(cahaya_provider, "get_settings", lambda: settings)
    params = {
        "req_ver": "1.0",
        "req_mode": "1",
        "req_time": str(int(time.time() * 1000)),
        "req_id": str(uuid.uuid4()),
        "req_params": json.dumps({
            "merchant_no": "merchant-id",
            "merchant_order_no": out_trade_no,
            "total_fee": "150000",
            "pay_type": "2",
            "order_state": "PAYSUCCESS",
            "out_trade_no": "cahaya-trade-1",
        }, separators=(",", ":")),
    }
    params["key_sign"] = sign_payload(json.loads(params["req_params"]), "access-token")

    async with SessionLocal() as db:
        assert await process_cahaya_notification(db, params) == "success"
    async with SessionLocal() as db:
        assert await process_cahaya_notification(db, params) == "success"
    async with SessionLocal() as db:
        user = await db.get(User, override_business_user)
        order = await db.get(RechargeOrder, order_id)
        ledgers = list(await db.scalars(select(CreditLedger).where(CreditLedger.recharge_order_id == order_id)))
        assert order.status == "paid"
        assert user.credit_balance >= 1000
        assert len(ledgers) == 1
