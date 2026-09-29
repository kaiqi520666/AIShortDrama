import hashlib
import hmac
import json
import time
import uuid
from typing import Any

import httpx

from app.core.config import get_settings


class CahayaError(RuntimeError):
    pass


def sign_payload(payload: dict[str, Any], access_token: str) -> str:
    values = sorted(
        (key, str(value)) for key, value in payload.items()
        if value is not None and key != "key_sign"
    )
    raw = "&".join(f"{key}={value}" for key, value in values)
    if raw:
        raw += "&"
    return hashlib.md5(f"{raw}access_token={access_token}".encode("utf-8")).hexdigest()


def _gateway_message(data: dict[str, Any], fallback: str) -> str:
    message = str(data.get("resp_msg") or "").strip()
    if not message or len(message) > 120:
        return fallback
    return message


def verify_payload(payload: dict[str, Any], access_token: str) -> bool:
    received = str(payload.get("key_sign") or "").lower()
    return bool(received) and hmac.compare_digest(received, sign_payload(payload, access_token))


class CahayaProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, *, require_enabled: bool = True):
        settings = get_settings()
        required = (settings.cahaya_merchant_no, settings.cahaya_terminal_no, settings.cahaya_access_token, settings.cahaya_notify_url)
        if require_enabled and not settings.cahaya_enabled:
            raise CahayaError("Cahaya QRIS 尚未启用")
        if not all(required):
            raise CahayaError("CAHAYA 支付配置不完整")
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=settings.cahaya_timeout_seconds, transport=transport)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    def _request(self, params: dict[str, Any], *, request_time: str | None = None) -> dict[str, Any]:
        now = request_time or str(int(time.time() * 1000))
        public = {"req_ver": "1.0", "req_mode": "1", "req_time": now, "req_id": str(uuid.uuid4()), "terminal_no": self.settings.cahaya_terminal_no, "req_params": json.dumps(params, ensure_ascii=False, separators=(",", ":"))}
        public["key_sign"] = sign_payload(public, self.settings.cahaya_access_token)
        return public

    async def create_payment(self, *, out_trade_no: str, amount_minor: int, terminal_ip: str) -> dict[str, Any]:
        request_time = str(int(time.time() * 1000))
        params = {"pay_ver": "100", "merchant_order_no": out_trade_no, "merchant_no": self.settings.cahaya_merchant_no, "terminal_no": self.settings.cahaya_terminal_no, "total_fee": str(amount_minor), "pay_type": "2", "terminal_ip": terminal_ip, "terminal_time": request_time, "time_expire": "7200", "notify_url": self.settings.cahaya_notify_url}
        try:
            response = await self.client.post(f"{self.settings.cahaya_gateway.rstrip('/')}/open/payment/prepay", json=self._request(params, request_time=request_time))
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise CahayaError("Cahaya 支付服务暂时不可用") from exc
        if str(data.get("resp_code")) != "10000":
            raise CahayaError(_gateway_message(data, "Cahaya 支付下单失败"))
        try:
            business = json.loads(data.get("resp_params") or "{}")
        except json.JSONDecodeError:
            business = {}
        if isinstance(business, dict) and business.get("pre_order_state") not in {None, "SUCCESS"}:
            raise CahayaError(_gateway_message({"resp_msg": business.get("pre_state_msg")}, "Cahaya 支付下单失败"))
        return data

    async def query_payment(self, *, out_trade_no: str) -> dict[str, Any]:
        params = {"pay_ver": "100", "merchant_order_no": out_trade_no, "merchant_no": self.settings.cahaya_merchant_no, "terminal_no": self.settings.cahaya_terminal_no}
        try:
            response = await self.client.post(f"{self.settings.cahaya_gateway.rstrip('/')}/open/payment/query", json=self._request(params))
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise CahayaError("Cahaya 支付查询失败") from exc
        if str(data.get("resp_code")) != "10000":
            raise CahayaError(_gateway_message(data, "Cahaya 支付查询失败"))
        return data

    def verify_notify(self, payload: dict[str, Any]) -> bool:
        timestamp = payload.get("req_time")
        try:
            sent_at = int(timestamp)
        except (TypeError, ValueError):
            return False
        if abs(int(time.time() * 1000) - sent_at) > 15 * 60 * 1000:
            return False
        try:
            business = json.loads(payload.get("req_params") or "")
        except (TypeError, json.JSONDecodeError):
            return False
        if not isinstance(business, dict):
            return False
        return verify_payload({**business, "key_sign": payload.get("key_sign")}, self.settings.cahaya_access_token)
