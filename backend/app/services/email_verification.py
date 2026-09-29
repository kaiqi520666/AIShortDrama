import hashlib
import hmac
import secrets
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import LocalizedValueError
from app.core.rate_limit import hashed_identifier, increment_fixed_window
from app.models import User
from app.providers.tencent_ses import send_verification_email
from app.providers.turnstile import TurnstileVerificationError, verify_turnstile


CODE_TTL_SECONDS = 600
COOLDOWN_SECONDS = 60
EMAIL_HOURLY_LIMIT = 5
IP_HOURLY_LIMIT = 20
MAX_VERIFY_ATTEMPTS = 5


class EmailVerificationError(LocalizedValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def _digest(email: str, code: str) -> str:
    return hmac.new(
        get_settings().secret_key.encode(),
        f"{email}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _keys(email: str) -> tuple[str, str, str, str]:
    prefix = get_settings().redis_prefix
    email_id = hashed_identifier(email)
    return (
        f"{prefix}:auth:email-code:value:{email_id}",
        f"{prefix}:auth:email-code:attempts:{email_id}",
        f"{prefix}:auth:email-code:cooldown:{email_id}",
        f"{prefix}:auth:email-code:email-limit:{email_id}",
    )


async def _check_limit(redis, key: str, limit: int, message: str) -> None:
    if await increment_fixed_window(redis, key, 3600) > limit:
        raise EmailVerificationError(message, error_key="rate_limited")


async def issue_registration_code(
    db: AsyncSession,
    redis,
    email: str,
    ip_address: str,
    captcha_token: str,
    *,
    send_email: Callable[[str, str], Awaitable[None]] = send_verification_email,
    verify_captcha: Callable[[str, str, str], Awaitable[None]] = verify_turnstile,
) -> None:
    email = normalize_email(email)
    try:
        await verify_captcha(captcha_token, ip_address, "register_email")
    except TurnstileVerificationError as exc:
        raise EmailVerificationError(str(exc), error_key="captcha_failed") from exc
    if await db.scalar(select(User.id).where(User.email == email)):
        raise EmailVerificationError("邮箱已注册", error_key="account_exists")

    code_key, attempts_key, cooldown_key, email_limit_key = _keys(email)
    if not await redis.set(cooldown_key, "1", ex=COOLDOWN_SECONDS, nx=True):
        raise EmailVerificationError("请稍后再发送验证码", error_key="code_cooldown")
    try:
        await _check_limit(
            redis,
            email_limit_key,
            EMAIL_HOURLY_LIMIT,
            "该邮箱发送过于频繁，请稍后再试",
        )
        await _check_limit(
            redis,
            f"{get_settings().redis_prefix}:auth:email-code:ip-limit:{hashed_identifier(ip_address)}",
            IP_HOURLY_LIMIT,
            "请求过于频繁，请稍后再试",
        )
        code = f"{secrets.randbelow(1_000_000):06d}"
        await redis.set(code_key, _digest(email, code), ex=CODE_TTL_SECONDS)
        await redis.delete(attempts_key)
        await send_email(email, code)
    except EmailVerificationError:
        raise
    except Exception as exc:
        await redis.delete(code_key, attempts_key, cooldown_key)
        raise EmailVerificationError("验证码邮件发送失败，请稍后重试", error_key="email_send_failed") from exc


async def consume_registration_code(redis, email: str, code: str) -> None:
    email = normalize_email(email)
    code_key, attempts_key, cooldown_key, _ = _keys(email)
    stored = await redis.get(code_key)
    if stored is None:
        raise EmailVerificationError("验证码已过期，请重新获取", error_key="code_expired")
    if isinstance(stored, bytes):
        stored = stored.decode()
    attempts = await redis.incr(attempts_key)
    if attempts == 1:
        await redis.expire(attempts_key, CODE_TTL_SECONDS)
    if not hmac.compare_digest(stored, _digest(email, code)):
        if attempts >= MAX_VERIFY_ATTEMPTS:
            await redis.delete(code_key, attempts_key)
            raise EmailVerificationError("验证码错误次数过多，请重新获取", error_key="code_attempts_exceeded")
        raise EmailVerificationError("验证码错误", error_key="code_invalid")
    await redis.delete(code_key, attempts_key, cooldown_key)
