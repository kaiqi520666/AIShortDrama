import asyncio
import uuid
import json
import time
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import CreditLedger, RechargeOrder, RechargeTier, User
from app.providers import cahaya as cahaya_provider
from app.providers.zpay import sign_params
from app.providers.cahaya import sign_payload, verify_payload
from app.services import recharge as recharge_service
from app.services.recharge import RechargeError, calculate_recharge, process_cahaya_notification, process_notification, sync_cahaya_order, validate_tiers


@pytest.fixture
def payment_settings(monkeypatch):
    settings = SimpleNamespace(
        zpay_key="secret", zpay_pid="merchant-1",
        cahaya_enabled=False, cahaya_merchant_no="merchant-id",
        cahaya_terminal_no="terminal-id", cahaya_access_token="access-token",
        cahaya_notify_url="https://example.com/notify", cahaya_timeout_seconds=20,
    )
    monkeypatch.setattr(recharge_service, "get_settings", lambda: settings)
    monkeypatch.setattr(cahaya_provider, "get_settings", lambda: settings)
    return settings


async def stored_order(user_id, provider_name, **values):
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        before = user.credit_balance
        order_id = uuid.uuid4()
        order = RechargeOrder(
            id=order_id,
            user_id=user_id,
            out_trade_no=f"payment{order_id.hex[:24]}",
            provider=provider_name,
            currency="IDR" if provider_name == "cahaya" else "CNY",
            amount_cents=0 if provider_name == "cahaya" else 3500,
            amount_minor=150000 if provider_name == "cahaya" else 3500,
            base_credits=1000,
            bonus_credits=0,
            total_credits=1000,
            tier_snapshot={},
        )
        for name, value in values.items():
            setattr(order, name, value)
        db.add(order)
        await db.commit()
        return order, before


def payment_notification(provider, order, *, trade_no="provider-trade", **changes):
    if provider == "zpay":
        params = {
            "pid": "merchant-1",
            "trade_status": "TRADE_SUCCESS",
            "out_trade_no": order.out_trade_no,
            "trade_no": trade_no,
            "money": "35.00",
            "sign_type": "MD5",
            **changes,
        }
        params["sign"] = sign_params(params, "secret")
        return params
    business = {
        "merchant_no": "merchant-id", "merchant_order_no": order.out_trade_no,
        "total_fee": "150000", "pay_type": "2", "order_state": "PAYSUCCESS",
        "out_trade_no": trade_no, **changes,
    }
    return {
        "req_ver": "1.0", "req_mode": "1", "req_time": str(int(time.time() * 1000)),
        "req_id": str(uuid.uuid4()), "req_params": json.dumps(business),
        "key_sign": sign_payload(business, "access-token"),
    }


async def notify(provider, params):
    async with SessionLocal() as db:
        handler = process_cahaya_notification if provider == "cahaya" else process_notification
        return await handler(db, params)


async def payment_state(order_id, user_id):
    async with SessionLocal() as db:
        order = await db.get(RechargeOrder, order_id)
        user = await db.get(User, user_id)
        ledgers = list(await db.scalars(
            select(CreditLedger).where(CreditLedger.recharge_order_id == order_id)
        ))
        return order, user.credit_balance, ledgers


def test_cahaya_signature_uses_sorted_public_fields_and_access_token_last():
    payload = {"terminal_no": "10005965", "req_ver": "1.0", "req_mode": "1", "req_time": "1772701701326", "req_id": "367799fe-e909-45b7-a91a-917c43cd8941", "req_params": '{"pay_type":"2"}'}
    signature = sign_payload(payload, "31cf7844f0ae4360adea6ca1a280f6ae")
    assert len(signature) == 32
    assert verify_payload({**payload, "key_sign": signature}, "31cf7844f0ae4360adea6ca1a280f6ae")
    assert not verify_payload({**payload, "key_sign": "wrong"}, "31cf7844f0ae4360adea6ca1a280f6ae")


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["prepay", "query"])
async def test_cahaya_sends_signed_json(operation):
    provider = cahaya_provider.CahayaProvider.__new__(cahaya_provider.CahayaProvider)
    provider.settings = SimpleNamespace(
        cahaya_terminal_no="terminal", cahaya_access_token="token",
        cahaya_merchant_no="merchant", cahaya_gateway="https://example.com",
        cahaya_notify_url="https://example.com/notify",
    )

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == f"/open/payment/{operation}"
        assert request.headers["content-type"] == "application/json"
        payload = json.loads(request.content)
        assert isinstance(payload["req_params"], str)
        assert verify_payload(payload, "token")
        business = json.loads(payload["req_params"])
        assert business["merchant_order_no"] == "test-order"
        if operation == "prepay":
            assert payload["req_time"] == business["terminal_time"]
            assert business["total_fee"] == "1200"
            assert business["pay_type"] == "2"
        return httpx.Response(200, json={"resp_code": "10000", "resp_params": "{}"})

    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with provider:
        if operation == "prepay":
            result = await provider.create_payment(
                out_trade_no="test-order", amount_minor=1200, terminal_ip="127.0.0.1",
            )
        else:
            result = await provider.query_payment(out_trade_no="test-order")
    assert result["resp_code"] == "10000"


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
        before = user.credit_balance
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
        assert user.credit_balance == before + 1000
        assert len(ledgers) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["zpay", "cahaya"])
async def test_failed_order_success_notification_is_recorded_without_crediting(
    payment_settings, override_business_user, provider,
):
    order, before = await stored_order(
        override_business_user, provider, status="failed", error_message="下单失败",
    )
    params = payment_notification(provider, order)
    assert await notify(provider, params) == "success"
    assert await notify(provider, params) == "success"
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "failed"
    assert saved.error_message == "下单失败"
    assert saved.paid_at is None
    assert saved.callback_received_at is not None
    assert saved.callback_payload["result"] == "failed_order"
    assert saved.callback_payload["request"]["sign" if provider == "zpay" else "key_sign"] == "[REDACTED]"
    assert balance == before
    assert ledgers == []


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["zpay", "cahaya"])
async def test_concurrent_notifications_credit_once(payment_settings, override_business_user, provider):
    order, before = await stored_order(override_business_user, provider)
    params = payment_notification(provider, order)
    assert await asyncio.gather(notify(provider, params), notify(provider, params)) == ["success", "success"]
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "paid"
    assert saved.callback_payload["result"] == "already_paid"
    assert balance == before + 1000
    assert len(ledgers) == 1
    assert ledgers[0].amount == 1000
    assert ledgers[0].balance_after == balance


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["zpay", "cahaya"])
@pytest.mark.parametrize("mismatch", ["amount", "currency", "provider"])
async def test_notification_rejects_order_mismatch(
    payment_settings, override_business_user, provider, mismatch,
):
    values = {}
    changes = {}
    if mismatch == "amount":
        changes["total_fee" if provider == "cahaya" else "money"] = "150001" if provider == "cahaya" else "36.00"
    elif mismatch == "currency":
        values["currency"] = "CNY" if provider == "cahaya" else "IDR"
    else:
        values["provider"] = "zpay" if provider == "cahaya" else "cahaya"
    order, before = await stored_order(override_business_user, provider, **values)
    assert await notify(provider, payment_notification(provider, order, **changes)) == "fail"
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "pending"
    assert saved.callback_payload["result"] == "rejected"
    assert balance == before
    assert ledgers == []


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["zpay", "cahaya"])
async def test_paid_order_requires_same_transaction_on_duplicate(
    payment_settings, override_business_user, provider,
):
    order, before = await stored_order(override_business_user, provider)
    assert await notify(provider, payment_notification(provider, order)) == "success"
    paid, _, _ = await payment_state(order.id, override_business_user)
    assert await notify(provider, payment_notification(provider, order, trade_no="another-trade")) == "fail"
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "paid"
    assert saved.provider_trade_no == "provider-trade"
    assert saved.paid_at == paid.paid_at
    assert saved.callback_payload["result"] == "rejected"
    assert balance == before + 1000
    assert len(ledgers) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["zpay", "cahaya"])
async def test_notification_requires_provider_transaction(
    payment_settings, override_business_user, provider,
):
    order, before = await stored_order(override_business_user, provider)
    assert await notify(provider, payment_notification(provider, order, trade_no="")) == "fail"
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "pending"
    assert balance == before
    assert ledgers == []


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["zpay", "cahaya"])
async def test_concurrent_orders_cannot_use_same_provider_transaction(
    payment_settings, override_business_user, provider,
):
    first, before = await stored_order(override_business_user, provider)
    second, _ = await stored_order(override_business_user, provider)
    results = await asyncio.gather(
        notify(provider, payment_notification(provider, first)),
        notify(provider, payment_notification(provider, second)),
    )
    assert sorted(results) == ["fail", "success"]
    first_state, balance, first_ledgers = await payment_state(first.id, override_business_user)
    second_state, _, second_ledgers = await payment_state(second.id, override_business_user)
    assert sorted([first_state.status, second_state.status]) == ["paid", "pending"]
    assert len(first_ledgers) + len(second_ledgers) == 1
    assert balance == before + 1000
    rejected = first if results[0] == "fail" else second
    saved, _, _ = await payment_state(rejected.id, override_business_user)
    assert saved.callback_payload["result"] == "rejected"


@pytest.mark.asyncio
async def test_existing_ledger_conflict_rolls_back_credit_and_allows_safe_retry(
    payment_settings, override_business_user,
):
    order, before = await stored_order(override_business_user, "zpay")
    async with SessionLocal() as db:
        db.add(CreditLedger(
            user_id=override_business_user, recharge_order_id=order.id,
            entry_type="recharge", amount=1000, balance_after=before, frozen_after=0,
            idempotency_key=f"recharge:{order.id}:paid",
        ))
        await db.commit()
    params = payment_notification("zpay", order)
    assert await notify("zpay", params) == "fail"
    assert await notify("zpay", params) == "fail"
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "pending"
    assert saved.provider_trade_no is None
    assert saved.paid_at is None
    assert saved.callback_payload["result"] == "rejected"
    assert balance == before
    assert len(ledgers) == 1


@pytest.mark.asyncio
async def test_cahaya_query_and_notification_share_idempotent_settlement(
    monkeypatch, payment_settings, override_business_user,
):
    order, before = await stored_order(override_business_user, "cahaya")

    class QueryProvider:
        calls = 0

        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def query_payment(self, *, out_trade_no):
            self.__class__.calls += 1
            return {"resp_params": json.dumps({
                "merchant_order_no": out_trade_no, "total_fee": "150000",
                "order_state": "PAYSUCCESS", "out_trade_no": "provider-trade",
            })}

    with monkeypatch.context() as patch:
        patch.setattr(recharge_service, "CahayaProvider", QueryProvider)
        async with SessionLocal() as db:
            saved = await db.get(RechargeOrder, order.id)
            await sync_cahaya_order(db, saved)
            await sync_cahaya_order(db, saved)
    assert QueryProvider.calls == 1
    assert await notify("cahaya", payment_notification("cahaya", order)) == "success"
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "paid"
    assert saved.callback_payload["result"] == "already_paid"
    assert balance == before + 1000
    assert len(ledgers) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("money", ["35.004", "35.005", "34.999", "NaN", "Infinity"])
async def test_zpay_notification_rejects_fractional_cent_amounts(
    payment_settings, override_business_user, money,
):
    order, before = await stored_order(override_business_user, "zpay")
    params = payment_notification("zpay", order, money=money)
    assert await notify("zpay", params) == "fail"
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "pending"
    assert balance == before
    assert not ledgers


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["zpay", "cahaya"])
async def test_settlement_refreshes_an_account_loaded_before_concurrent_balance_update(
    override_business_user, provider,
):
    order, before = await stored_order(override_business_user, provider)
    async with SessionLocal() as db:
        cached_user = await db.get(User, override_business_user)
        cached_order = await db.get(RechargeOrder, order.id)
        async with SessionLocal() as concurrent_db:
            concurrent_user = await concurrent_db.get(User, override_business_user)
            concurrent_user.credit_balance += 75
            concurrent_user.credit_frozen += 25
            expected_frozen = concurrent_user.credit_frozen
            await concurrent_db.commit()
        assert cached_user.credit_balance == before
        assert await recharge_service.settle_recharge_order(
            db, cached_order, "provider-trade"
        ) == "paid"
        await db.commit()
        assert cached_user.credit_balance == before + 75 + 1000
        assert cached_user.credit_frozen == expected_frozen
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "paid"
    assert balance == before + 75 + 1000
    assert len(ledgers) == 1
    assert ledgers[0].balance_after == balance
    assert ledgers[0].frozen_after == expected_frozen


@pytest.mark.asyncio
async def test_create_timeout_does_not_downgrade_an_order_already_paid_by_callback(
    monkeypatch, payment_settings, override_business_user,
):
    class TimeoutAfterPaymentProvider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def create_payment(self, *, order_id, **_kwargs):
            async with SessionLocal() as db:
                order = await db.get(RechargeOrder, uuid.UUID(order_id))
            assert await notify("zpay", payment_notification("zpay", order)) == "success"
            raise recharge_service.ZPayError("请求超时")

    monkeypatch.setattr(recharge_service, "ZPayProvider", TimeoutAfterPaymentProvider)
    async with SessionLocal() as db:
        user = await db.get(User, override_business_user)
        before = user.credit_balance
        order = await recharge_service.create_order(db, user, 3500, "8.8.8.8")
        assert order.status == "paid"
        assert user.credit_balance == before + 1000
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "paid"
    assert balance == before + 1000
    assert len(ledgers) == 1


@pytest.mark.asyncio
async def test_create_response_cannot_replace_a_transaction_already_settled_by_callback(
    monkeypatch, payment_settings, override_business_user,
):
    order_ids = []

    class ConflictingResponseProvider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def create_payment(self, *, order_id, **_kwargs):
            order_ids.append(uuid.UUID(order_id))
            async with SessionLocal() as db:
                order = await db.get(RechargeOrder, uuid.UUID(order_id))
            assert await notify("zpay", payment_notification("zpay", order)) == "success"
            return {"trade_no": "different-prepay-trade"}

    monkeypatch.setattr(recharge_service, "ZPayProvider", ConflictingResponseProvider)
    async with SessionLocal() as db:
        user = await db.get(User, override_business_user)
        before = user.credit_balance
        with pytest.raises(RechargeError, match="交易号不匹配"):
            await recharge_service.create_order(db, user, 3500, "8.8.8.8")
    saved, balance, ledgers = await payment_state(order_ids[0], override_business_user)
    assert saved.status == "paid"
    assert saved.provider_trade_no == "provider-trade"
    assert balance == before + 1000
    assert len(ledgers) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("body", ["[]", "null"])
async def test_cahaya_query_invalid_business_response_does_not_settle(
    monkeypatch, payment_settings, override_business_user, body,
):
    order, before = await stored_order(override_business_user, "cahaya")

    class QueryProvider:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def query_payment(self, **_kwargs):
            return {"resp_params": body}

    monkeypatch.setattr(recharge_service, "CahayaProvider", QueryProvider)
    async with SessionLocal() as db:
        saved = await db.get(RechargeOrder, order.id)
        with pytest.raises(RechargeError, match="支付状态查询失败"):
            await sync_cahaya_order(db, saved)
        await db.rollback()
    saved, balance, ledgers = await payment_state(order.id, override_business_user)
    assert saved.status == "pending"
    assert balance == before
    assert not ledgers
