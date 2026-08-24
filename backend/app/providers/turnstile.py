import logging

import httpx

from app.core.config import get_settings


VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
logger = logging.getLogger(__name__)


class TurnstileVerificationError(ValueError):
    pass


async def verify_turnstile(token: str, ip_address: str, action: str) -> None:
    secret = get_settings().turnstile_secret_key
    if not token:
        raise TurnstileVerificationError("请完成人机验证")
    if not secret:
        raise TurnstileVerificationError("人机验证服务暂时不可用，请稍后重试")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                VERIFY_URL,
                data={"secret": secret, "response": token, "remoteip": ip_address},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Turnstile verification request failed", exc_info=exc)
        raise TurnstileVerificationError("人机验证服务暂时不可用，请稍后重试") from exc
    if not payload.get("success") or payload.get("action") != action:
        raise TurnstileVerificationError("请重新完成人机验证")
