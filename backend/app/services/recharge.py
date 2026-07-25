import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import CreditLedger, RechargeOrder, RechargeTier, User
from app.providers.zpay import ZPayError, ZPayProvider, parse_amount_cents, verify_signature

MIN_RECHARGE_CENTS = 3500
MAX_RECHARGE_CENTS = 350000


class RechargeError(RuntimeError):
    pass


@dataclass(slots=True)
class RechargeQuote:
    tier: RechargeTier
    base_credits: int
    bonus_credits: int

    @property
    def total_credits(self) -> int:
        return self.base_credits + self.bonus_credits


def tier_data(tier: RechargeTier) -> dict[str, Any]:
    return {
        "id": str(tier.id),
        "min_amount_cents": tier.min_amount_cents,
        "bonus_rate_bps": tier.bonus_rate_bps,
        "enabled": tier.enabled,
        "created_at": tier.created_at.isoformat() if tier.created_at else None,
        "updated_at": tier.updated_at.isoformat() if tier.updated_at else None,
    }


def order_data(order: RechargeOrder, credit_balance: int | None = None) -> dict[str, Any]:
    return {
        "id": str(order.id),
        "out_trade_no": order.out_trade_no,
        "provider_trade_no": order.provider_trade_no,
        "amount_cents": order.amount_cents,
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


async def calculate_recharge(db: AsyncSession, amount_cents: int) -> RechargeQuote:
    if amount_cents < MIN_RECHARGE_CENTS or amount_cents > MAX_RECHARGE_CENTS or amount_cents % 100:
        raise RechargeError("充值金额必须为 35–3500 元的整数")
    tier = await db.scalar(
        select(RechargeTier)
        .where(RechargeTier.enabled.is_(True), RechargeTier.min_amount_cents <= amount_cents)
        .order_by(RechargeTier.min_amount_cents.desc())
        .limit(1)
    )
    if not tier:
        raise RechargeError("当前没有可用的充值阶梯")
    base_credits = amount_cents * 1000 // 3500
    bonus_credits = base_credits * tier.bonus_rate_bps // 10000
    return RechargeQuote(tier, base_credits, bonus_credits)


def validate_tiers(tiers: list[RechargeTier]) -> None:
    enabled = sorted((tier for tier in tiers if tier.enabled), key=lambda tier: tier.min_amount_cents)
    if not enabled or enabled[0].min_amount_cents != MIN_RECHARGE_CENTS:
        raise RechargeError("启用阶梯必须从 35 元开始")
    if any(current.bonus_rate_bps < previous.bonus_rate_bps for previous, current in zip(enabled, enabled[1:])):
        raise RechargeError("金额越高，赠送比例不能降低")


def _out_trade_no() -> str:
    return f"{datetime.now(UTC):%y%m%d%H%M%S}{uuid.uuid4().int % 10**8:08d}"


async def create_order(db: AsyncSession, user: User, amount_cents: int, client_ip: str) -> RechargeOrder:
    quote = await calculate_recharge(db, amount_cents)
    try:
        provider = ZPayProvider()
    except ZPayError as exc:
        raise RechargeError(str(exc)) from exc
    order = RechargeOrder(
        user_id=user.id,
        tier_id=quote.tier.id,
        out_trade_no=_out_trade_no(),
        amount_cents=amount_cents,
        base_credits=quote.base_credits,
        bonus_credits=quote.bonus_credits,
        total_credits=quote.total_credits,
        tier_snapshot={
            "tier_id": str(quote.tier.id),
            "min_amount_cents": quote.tier.min_amount_cents,
            "bonus_rate_bps": quote.tier.bonus_rate_bps,
        },
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    try:
        async with provider:
            result = await provider.create_payment(
                order_id=str(order.id),
                out_trade_no=order.out_trade_no,
                amount_cents=order.amount_cents,
                client_ip=client_ip,
            )
    except ZPayError as exc:
        order.status = "failed"
        order.error_message = str(exc)[:255]
        await db.commit()
        raise RechargeError(str(exc)) from exc
    order.provider_trade_no = str(result.get("trade_no") or result.get("O_id") or "") or None
    order.pay_url = result.get("payurl") or None
    order.qr_code = result.get("qrcode") or None
    order.qr_img = result.get("img") or None
    await db.commit()
    await db.refresh(order)
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

    async with db.begin():
        order = await db.scalar(
            select(RechargeOrder)
            .where(RechargeOrder.out_trade_no == out_trade_no)
            .with_for_update()
        )
        if not order or order.amount_cents != amount_cents:
            return "fail"
        if order.status == "paid":
            return "success"
        user = await db.scalar(select(User).where(User.id == order.user_id).with_for_update())
        if not user:
            return "fail"
        order.status = "paid"
        order.provider_trade_no = params.get("trade_no") or order.provider_trade_no
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
                note=f"充值 {order.amount_cents // 100} 元，赠送 {order.bonus_credits} 积分",
            )
        )
    return "success"
