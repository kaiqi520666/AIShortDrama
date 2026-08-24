from dataclasses import dataclass

from app.core.config import get_settings
from app.core.rate_limit import hashed_identifier, increment_fixed_window


LOGIN_WINDOW_SECONDS = 900
EMAIL_CAPTCHA_THRESHOLD = 3
IP_CAPTCHA_THRESHOLD = 10
IP_FAILURE_LIMIT = 30


@dataclass(frozen=True)
class LoginSecurityState:
    captcha_required: bool
    rate_limited: bool
    retry_after_seconds: int | None = None


def _failure_keys(email: str, ip_address: str) -> tuple[str, str]:
    prefix = get_settings().redis_prefix
    return (
        f"{prefix}:auth:login:email:{hashed_identifier(email)}",
        f"{prefix}:auth:login:ip:{hashed_identifier(ip_address)}",
    )


async def get_login_security_state(redis, email: str, ip_address: str) -> LoginSecurityState:
    email_key, ip_key = _failure_keys(email, ip_address)
    email_failures, ip_failures = await redis.get(email_key), await redis.get(ip_key)
    email_failures = int(email_failures or 0)
    ip_failures = int(ip_failures or 0)
    if ip_failures >= IP_FAILURE_LIMIT:
        return LoginSecurityState(True, True, max(int(await redis.ttl(ip_key)), 1))
    return LoginSecurityState(
        email_failures >= EMAIL_CAPTCHA_THRESHOLD or ip_failures >= IP_CAPTCHA_THRESHOLD,
        False,
    )


async def record_login_failure(redis, email: str, ip_address: str) -> LoginSecurityState:
    email_key, ip_key = _failure_keys(email, ip_address)
    await increment_fixed_window(redis, email_key, LOGIN_WINDOW_SECONDS)
    await increment_fixed_window(redis, ip_key, LOGIN_WINDOW_SECONDS)
    return await get_login_security_state(redis, email, ip_address)


async def clear_login_failures(redis, email: str, ip_address: str) -> None:
    await redis.delete(*_failure_keys(email, ip_address))
