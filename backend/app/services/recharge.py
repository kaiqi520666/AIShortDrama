import ipaddress
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import public_error_message
from app.models import BillingPolicy, CreditLedger, RechargeOrder, RechargeTier, User
from app.providers.cahaya import CahayaError, CahayaProvider
from app.providers.zpay import ZPayError, ZPayProvider, parse_amount_cents, verify_signature
from app.services.admin_configuration import get_billing_policy, policy_snapshot


logger = logging.getLogger(__name__)


class RechargeError(RuntimeError):
    def __init__(self, message: str, status_code: int = 422, *, error_key: str | None = None, error_params: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_key = error_key or ("payment_unavailable" if status_code == 503 else "invalid_request")
        self.error_params = error_params or {}


@dataclass(slots=True)
class RechargeQuote:
    tier: RechargeTier
    policy: BillingPolicy
    base_credits: int
    bonus_credits: int

    @property
    def total_credits(self) -> int:
        return self.base_credits + self.bonus_credits


def tier_data(tier: RechargeTier) -> dict[str, Any]:
    return {
        "id": str(tier.id),
        "currency": tier.currency,
        "min_amount_cents": tier.min_amount_cents,
        "bonus_rate_bps": tier.bonus_rate_bps,
        "enabled": tier.enabled,
        "created_at": tier.created_at.isoformat() if tier.created_at else None,
        "updated_at": tier.updated_at.isoformat() if tier.updated_at else None,
    }


def order_data(order: RechargeOrder, credit_balance: int | None = None) -> dict[str, Any]:
    data = {
        "id": str(order.id),
        "out_trade_no": order.out_trade_no,
        "provider_trade_no": order.provider_trade_no,
        "amount_cents": order.amount_cents,
        "amount_minor": order.amount_minor or order.amount_cents,
        "currency": order.currency,
        "provider": order.provider,
        "base_credits": order.base_credits,
        "bonus_credits": order.bonus_credits,
        "total_credits": order.total_credits,
        "bonus_rate_bps": order.tier_snapshot.get("bonus_rate_bps", 0),
        "pay_type": order.pay_type,
        "status": order.status,
        "pay_url": order.pay_url,
        "qr_code": order.qr_code,
        "qr_img": order.qr_img,
        "error_message": order.error_message,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        **({"credit_balance": credit_balance} if credit_balance is not None else {}),
    }
    return data


def _redact_snapshot(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            str(item_key): "[REDACTED]"
            if str(item_key).lower() == "sign"
            or any(token in str(item_key).lower() for token in ("token", "secret", "password", "signature", "key_sign"))
            else _redact_snapshot(item, str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_snapshot(item, key) for item in value]
    return value


def admin_order_data(order: RechargeOrder) -> dict[str, Any]:
    return {
        **order_data(order),
        "tier_snapshot": _redact_snapshot(order.tier_snapshot),
        "provider_payload": _redact_snapshot(order.provider_payload),
        "callback_payload": _redact_snapshot(order.callback_payload),
        "callback_received_at": order.callback_received_at.isoformat() if order.callback_received_at else None,
    }


async def calculate_recharge(db: AsyncSession, amount_cents: int, *, currency: str = "CNY") -> RechargeQuote:
    policy = await get_billing_policy(db)
    is_idr = currency == "IDR"
    minimum = policy.idr_recharge_min if is_idr else policy.recharge_min_cents
    maximum = policy.idr_recharge_max if is_idr else policy.recharge_max_cents
    unit_amount = policy.idr_unit_amount if is_idr else policy.unit_amount_cents
    unit_credits = policy.idr_unit_credits if is_idr else policy.unit_credits
    if amount_cents < minimum or amount_cents > maximum or (not is_idr and amount_cents % 100):
        raise RechargeError(
            "充值金额不在允许范围内",
            error_key="recharge_amount", error_params={"min": minimum, "max": maximum, "currency": currency},
        )
    tier = await db.scalar(
        select(RechargeTier)
        .where(
            RechargeTier.enabled.is_(True),
            RechargeTier.currency == currency,
            RechargeTier.min_amount_cents <= amount_cents,
        )
        .order_by(RechargeTier.min_amount_cents.desc())
        .limit(1)
    )
    if not tier:
        raise RechargeError("当前没有可用的充值阶梯", error_key="recharge_unavailable")
    base_credits = amount_cents * unit_credits // unit_amount
    bonus_credits = base_credits * tier.bonus_rate_bps // 10000
    return RechargeQuote(tier, policy, base_credits, bonus_credits)


def validate_tiers(tiers: list[RechargeTier], policy: BillingPolicy) -> None:
    currency_policies = [("CNY", policy.recharge_min_cents)]
    if hasattr(policy, "idr_recharge_min"):
        currency_policies.append(("IDR", policy.idr_recharge_min))
    for currency, minimum in currency_policies:
        enabled = sorted(
            (tier for tier in tiers if tier.enabled and getattr(tier, "currency", "CNY") == currency),
            key=lambda tier: tier.min_amount_cents,
        )
        if not enabled or not any(tier.min_amount_cents == minimum for tier in enabled):
            if currency == "CNY":
                message = f"启用阶梯必须包含 {minimum // 100} 元基础档"
            else:
                message = "IDR 启用阶梯必须包含基础档"
            raise RechargeError(message, error_key="recharge_base_tier")
        if any(current.bonus_rate_bps < previous.bonus_rate_bps for previous, current in zip(enabled, enabled[1:])):
            raise RechargeError("金额越高，赠送比例不能降低", error_key="recharge_bonus_order")


_DEV_TERMINAL_IP = "8.8.8.8"


def _cahaya_terminal_ip(value: str) -> str:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        ip = None
    if ip is not None and ip.version == 4 and ip.is_global:
        return value
    if get_settings().app_env != "production":
        return _DEV_TERMINAL_IP
    raise RechargeError(
        "Cahaya 需要付款设备的公网 IPv4，请通过公网地址打开充值页后再支付",
        error_key="cahaya_public_ip",
    )


def _payment_error_message(exc: Exception) -> str:
    if isinstance(exc, (ZPayError, CahayaError)) and str(exc):
        return str(exc)
    return public_error_message(exc, "支付服务暂时不可用")


def _out_trade_no() -> str:
    return f"{datetime.now(UTC):%y%m%d%H%M%S}{uuid.uuid4().int % 10**8:08d}"


async def create_order(db: AsyncSession, user: User, amount_cents: int, client_ip: str, *, provider_name: str = "zpay", amount_minor: int | None = None) -> RechargeOrder:
    if provider_name == "cahaya" and amount_minor is None:
        raise RechargeError("Cahaya 订单缺少印尼盾金额", error_key="recharge_amount")
    if provider_name == "cahaya":
        client_ip = _cahaya_terminal_ip(client_ip)
    currency = "IDR" if provider_name == "cahaya" else "CNY"
    actual_amount = amount_minor if provider_name == "cahaya" else amount_cents
    quote = await calculate_recharge(db, actual_amount, currency=currency)
    try:
        provider = CahayaProvider() if provider_name == "cahaya" else ZPayProvider()
    except (ZPayError, CahayaError) as exc:
        raise RechargeError(_payment_error_message(exc), status_code=503) from exc
    order = RechargeOrder(
        user_id=user.id,
        tier_id=quote.tier.id,
        out_trade_no=_out_trade_no(),
        amount_cents=amount_cents,
        amount_minor=actual_amount,
        currency=currency,
        provider=provider_name,
        base_credits=quote.base_credits,
        bonus_credits=quote.bonus_credits,
        total_credits=quote.total_credits,
        tier_snapshot={
            "tier_id": str(quote.tier.id),
            "min_amount_cents": quote.tier.min_amount_cents,
            "bonus_rate_bps": quote.tier.bonus_rate_bps,
            "billing_policy": policy_snapshot(quote.policy),
            "currency": currency,
            "amount_minor": actual_amount,
        },
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    try:
        async with provider:
            if provider_name == "cahaya":
                result = await provider.create_payment(out_trade_no=order.out_trade_no, amount_minor=actual_amount, terminal_ip=client_ip)
            else:
                result = await provider.create_payment(order_id=str(order.id), out_trade_no=order.out_trade_no, amount_cents=order.amount_cents, client_ip=client_ip)
    except (ZPayError, CahayaError) as exc:
        message = _payment_error_message(exc)
        order = await db.scalar(
            select(RechargeOrder)
            .where(RechargeOrder.id == order.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if order.status == "pending":
            order.status = "failed"
            order.error_message = message[:255]
        await db.commit()
        if order.status == "paid":
            await db.refresh(user)
            return order
        raise RechargeError(message, status_code=503) from exc
    response_params = json.loads(result.get("resp_params") or "{}") if provider_name == "cahaya" else {}
    provider_trade_no = (
        response_params.get("out_trade_no")
        if provider_name == "cahaya"
        else str(result.get("trade_no") or result.get("O_id") or "") or None
    )
    order = await db.scalar(
        select(RechargeOrder)
        .where(RechargeOrder.id == order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order.status == "paid" and provider_trade_no and order.provider_trade_no != provider_trade_no:
        raise RechargeError("下单结果与已支付订单的交易号不匹配")
    if order.status == "pending":
        order.provider_trade_no = provider_trade_no or order.provider_trade_no
    order.pay_url = result.get("payurl") or None
    order.qr_code = result.get("qrcode") or None
    order.qr_img = result.get("img") or None
    order.provider_payload = result
    if provider_name == "cahaya":
        order.qr_code = response_params.get("qr_code")
        order.pay_type = "qris"
    await db.commit()
    await db.refresh(order)
    await db.refresh(user)
    return order


async def process_notification(
    db: AsyncSession, params: dict[str, str]
) -> Literal["success", "fail"]:
    settings = get_settings()
    if not settings.zpay_key or not settings.zpay_pid:
        return "fail"
    if not verify_signature(params, settings.zpay_key):
        return "fail"
    if str(params.get("pid") or "") != settings.zpay_pid:
        return "fail"
    if params.get("trade_status") != "TRADE_SUCCESS":
        return "success"
    amount_cents = parse_amount_cents(params.get("money"))
    out_trade_no = params.get("out_trade_no")
    if amount_cents is None or not out_trade_no:
        return "fail"
    try:
        precise_amount = Decimal(params["money"]) * 100
    except (InvalidOperation, TypeError, ValueError):
        return "fail"
    if not precise_amount.is_finite() or precise_amount != amount_cents:
        return "fail"

    async with db.begin():
        order = await db.scalar(
            select(RechargeOrder)
            .where(RechargeOrder.out_trade_no == out_trade_no)
            .with_for_update()
        )
        if not order:
            return "fail"
        return await _process_order_payment(
            db,
            order,
            provider="zpay",
            currency="CNY",
            amount=amount_cents,
            provider_trade_no=params.get("trade_no"),
            snapshot={"request": _redact_snapshot(params)},
        )


async def process_cahaya_notification(db: AsyncSession, form: Any) -> Literal["success", "fail"]:
    settings = get_settings()
    if hasattr(form, "multi_items"):
        params = {str(key): str(value) for key, value in form.multi_items()}
    else:
        params = {str(key): str(value) for key, value in dict(form).items()}
    try:
        provider = CahayaProvider(require_enabled=False)
    except CahayaError:
        return "fail"
    async with provider:
        if not provider.verify_notify(params):
            return "fail"
    try:
        payload = json.loads(params.get("req_params") or "{}")
    except json.JSONDecodeError:
        return "fail"
    if not isinstance(payload, dict):
        return "fail"
    if payload.get("merchant_no") != settings.cahaya_merchant_no or payload.get("pay_type") != "2":
        return "fail"
    if payload.get("order_state") != "PAYSUCCESS":
        return "success"
    if payload.get("terminal_no") and payload.get("terminal_no") != settings.cahaya_terminal_no:
        return "fail"
    out_trade_no = payload.get("merchant_order_no")
    try:
        amount_minor = int(payload.get("total_fee") or 0)
    except (TypeError, ValueError):
        return "fail"
    if not out_trade_no or amount_minor <= 0:
        return "fail"
    async with db.begin():
        order = await db.scalar(select(RechargeOrder).where(RechargeOrder.out_trade_no == out_trade_no).with_for_update())
        if not order:
            return "fail"
        return await _process_order_payment(
            db,
            order,
            provider="cahaya",
            currency="IDR",
            amount=amount_minor,
            provider_trade_no=payload.get("out_trade_no"),
            snapshot={"request": _redact_snapshot(params), "params": _redact_snapshot(payload)},
        )


async def _process_order_payment(
    db: AsyncSession,
    order: RechargeOrder,
    *,
    provider: str,
    currency: str,
    amount: int,
    provider_trade_no: str | None,
    snapshot: dict[str, Any],
) -> Literal["success", "fail"]:
    expected_amount = order.amount_minor if provider == "cahaya" else order.amount_cents
    try:
        if order.provider != provider or order.currency != currency or expected_amount != amount:
            raise RechargeError("支付通知与订单信息不匹配")
        outcome = await settle_recharge_order(db, order, provider_trade_no)
    except RechargeError as exc:
        outcome = "rejected"
        snapshot = {**snapshot, "reason": str(exc)}
    order.callback_received_at = datetime.now(UTC)
    order.callback_payload = {**snapshot, "result": outcome}
    log = logger.warning if outcome in {"rejected", "failed_order"} else logger.info
    log(
        "recharge_callback_processed",
        extra={"order_id": str(order.id), "provider": provider, "status": order.status, "result": outcome},
    )
    return "fail" if outcome == "rejected" else "success"


async def settle_recharge_order(
    db: AsyncSession,
    order: RechargeOrder,
    provider_trade_no: str | None = None,
) -> Literal["paid", "already_paid", "failed_order"]:
    order = await db.scalar(
        select(RechargeOrder)
        .where(RechargeOrder.id == order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not order:
        raise RechargeError("充值订单不存在", status_code=404, error_key="not_found")
    provider_trade_no = str(provider_trade_no or "").strip()
    if not provider_trade_no:
        raise RechargeError("支付交易号缺失")
    if order.provider_trade_no and order.provider_trade_no != provider_trade_no:
        raise RechargeError("支付交易号与订单不匹配")
    if order.status == "paid":
        if order.provider_trade_no != provider_trade_no:
            raise RechargeError("已支付订单缺少一致的支付交易号")
        return "already_paid"
    if order.status == "failed":
        return "failed_order"
    if order.status != "pending":
        raise RechargeError("充值订单状态无效")
    existing = await db.scalar(
        select(RechargeOrder.id).where(
            RechargeOrder.provider == order.provider,
            RechargeOrder.provider_trade_no == provider_trade_no,
            RechargeOrder.id != order.id,
        )
    )
    if existing:
        raise RechargeError("支付交易号已关联其他订单", error_key="invalid_request")
    try:
        async with db.begin_nested():
            user = await db.scalar(
                select(User)
                .where(User.id == order.user_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if not user:
                raise RechargeError("充值用户不存在", status_code=404, error_key="not_found")
            order.status = "paid"
            order.provider_trade_no = provider_trade_no
            order.paid_at = datetime.now(UTC)
            order.error_message = None
            user.credit_balance += order.total_credits
            db.add(
                CreditLedger(
                    user_id=user.id,
                    recharge_order_id=order.id,
                    entry_type="recharge",
                    amount=order.total_credits,
                    balance_after=user.credit_balance,
                    frozen_after=user.credit_frozen,
                    idempotency_key=f"recharge:{order.id}:paid",
                    note=f"充值 {order.currency} {order.amount_minor or order.amount_cents}，赠送 {order.bonus_credits} 积分",
                )
            )
            await db.flush()
    except IntegrityError as exc:
        await db.refresh(order)
        raise RechargeError("充值结算记录冲突，请人工核查", error_key="invalid_request") from exc
    return "paid"


async def sync_cahaya_order(db: AsyncSession, order: RechargeOrder) -> RechargeOrder:
    if order.provider != "cahaya" or order.status != "pending":
        return order
    order = await db.scalar(
        select(RechargeOrder)
        .where(RechargeOrder.id == order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not order or order.status != "pending":
        return order
    if order.currency != "IDR":
        raise RechargeError("支付状态查询币种不匹配", error_key="invalid_request")
    try:
        async with CahayaProvider(require_enabled=False) as provider:
            result = await provider.query_payment(out_trade_no=order.out_trade_no)
    except CahayaError as exc:
        raise RechargeError("支付状态查询失败", status_code=503, error_key="payment_unavailable") from exc
    try:
        params = json.loads(result.get("resp_params") or "{}")
    except json.JSONDecodeError as exc:
        raise RechargeError("支付状态查询失败", status_code=503, error_key="payment_unavailable") from exc
    if not isinstance(params, dict):
        raise RechargeError("支付状态查询失败", status_code=503, error_key="payment_unavailable")
    order.provider_payload = {"query": result}
    if params.get("merchant_order_no") != order.out_trade_no:
        raise RechargeError("支付状态查询订单不匹配", error_key="invalid_request")
    try:
        queried_amount = int(params.get("total_fee") or 0)
    except (TypeError, ValueError) as exc:
        raise RechargeError("支付状态查询金额无效", error_key="invalid_request") from exc
    if queried_amount != order.amount_minor:
        raise RechargeError("支付状态查询金额不匹配", error_key="invalid_request")
    if params.get("order_state") == "PAYSUCCESS":
        await settle_recharge_order(db, order, params.get("out_trade_no"))
    await db.commit()
    await db.refresh(order)
    return order
