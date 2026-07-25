import hashlib
import hmac
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import httpx

from app.core.config import get_settings


class ZPayError(RuntimeError):
    pass


def format_amount(amount_cents: int) -> str:
    amount = (Decimal(amount_cents) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount:.2f}"


def parse_amount_cents(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int((Decimal(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except Exception:
        return None


def sign_params(params: dict[str, Any], key: str) -> str:
    items = sorted(
        (name, str(value))
        for name, value in params.items()
        if name not in {"sign", "sign_type"} and value is not None and str(value) != ""
    )
    raw = "&".join(f"{name}={value}" for name, value in items)
    return hashlib.md5(f"{raw}{key}".encode()).hexdigest()


def verify_signature(params: dict[str, str], key: str) -> bool:
    received = (params.get("sign") or "").lower()
    return bool(received) and hmac.compare_digest(received, sign_params(params, key))


class ZPayProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        settings = get_settings()
        if not all(
            (settings.zpay_pid, settings.zpay_key, settings.zpay_notify_url, settings.zpay_return_url)
        ):
            raise ZPayError("ZPAY 支付配置不完整")
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=20, transport=transport)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    async def create_payment(self, *, order_id: str, out_trade_no: str, amount_cents: int, client_ip: str) -> dict[str, Any]:
        payload = {
            "pid": self.settings.zpay_pid,
            "type": "wxpay",
            "out_trade_no": out_trade_no,
            "notify_url": self.settings.zpay_notify_url,
            "return_url": self.settings.zpay_return_url,
            "name": "MoonCut AI 积分充值",
            "money": format_amount(amount_cents),
            "clientip": client_ip,
            "device": "pc",
            "param": order_id,
            "sign_type": "MD5",
        }
        payload["sign"] = sign_params(payload, self.settings.zpay_key)
        try:
            response = await self.client.post(
                f"{self.settings.zpay_gateway.rstrip('/')}/mapi.php", data=payload
            )
            data = response.json()
        except Exception as exc:
            raise ZPayError("支付订单创建失败，请稍后重试") from exc
        if str(data.get("code")) != "1":
            raise ZPayError(str(data.get("msg") or "支付订单创建失败"))
        return data
