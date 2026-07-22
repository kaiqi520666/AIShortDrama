import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Response
from pwdlib import PasswordHash

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_COOKIE = "aisd_access"
REFRESH_COOKIE = "aisd_refresh"
password_hash = PasswordHash.recommended()

ROTATE_SESSION_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if not current then return 0 end
if current ~= ARGV[1] then
  redis.call('DEL', KEYS[1])
  return -1
end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
return 1
"""


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("密码至少需要 8 个字符")
    if len(password) > 72:
        raise ValueError("密码不能超过 72 个字符")


def hash_password(password: str) -> str:
    validate_password(password)
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hash.verify(password, encoded)
    except Exception:
        return False


def create_token(
    user_id: uuid.UUID,
    auth_version: int,
    token_type: str,
    expires_delta: timedelta,
    *,
    token_id: str | None = None,
    session_id: str | None = None,
) -> tuple[str, str]:
    now = datetime.now(UTC)
    token_id = token_id or uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "ver": auth_version,
        "jti": token_id,
        "iat": now,
        "exp": now + expires_delta,
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM), token_id


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        get_settings().secret_key,
        algorithms=[ALGORITHM],
        options={"require": ["sub", "type", "ver", "jti", "iat", "exp"]},
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("token 类型无效")
    if expected_type == "refresh" and not payload.get("sid"):
        raise jwt.InvalidTokenError("refresh token 缺少会话")
    return payload


def issue_tokens(
    user_id: uuid.UUID,
    auth_version: int,
    *,
    session_id: str | None = None,
    refresh_token_id: str | None = None,
) -> tuple[str, str, str, str]:
    settings = get_settings()
    session_id = session_id or uuid.uuid4().hex
    access_token, _ = create_token(
        user_id,
        auth_version,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token, refresh_token_id = create_token(
        user_id,
        auth_version,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
        token_id=refresh_token_id,
        session_id=session_id,
    )
    return access_token, refresh_token, session_id, refresh_token_id


def session_key(session_id: str) -> str:
    return f"{get_settings().redis_prefix}:auth:session:{session_id}"


def session_payload(user_id: uuid.UUID, auth_version: int, token_id: str) -> str:
    return json.dumps(
        {"user_id": str(user_id), "ver": auth_version, "jti": token_id},
        separators=(",", ":"),
        sort_keys=True,
    )


async def create_refresh_session(
    redis,
    user_id: uuid.UUID,
    auth_version: int,
) -> tuple[str, str]:
    access, refresh, session_id, token_id = issue_tokens(user_id, auth_version)
    ttl = get_settings().refresh_token_expire_days * 86400
    await redis.set(
        session_key(session_id),
        session_payload(user_id, auth_version, token_id),
        ex=ttl,
    )
    return access, refresh


async def rotate_refresh_session(
    redis,
    claims: dict[str, Any],
) -> tuple[str, str] | None:
    user_id = uuid.UUID(claims["sub"])
    auth_version = int(claims["ver"])
    session_id = claims["sid"]
    current_payload = session_payload(user_id, auth_version, claims["jti"])
    new_token_id = uuid.uuid4().hex
    new_payload = session_payload(user_id, auth_version, new_token_id)
    ttl = get_settings().refresh_token_expire_days * 86400
    result = await redis.eval(
        ROTATE_SESSION_SCRIPT,
        1,
        session_key(session_id),
        current_payload,
        new_payload,
        ttl,
    )
    if int(result) != 1:
        return None
    access, refresh, _, _ = issue_tokens(
        user_id,
        auth_version,
        session_id=session_id,
        refresh_token_id=new_token_id,
    )
    return access, refresh


async def revoke_refresh_session(redis, session_id: str) -> None:
    await redis.delete(session_key(session_id))


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/api",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/api/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/api")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


def login_failure_key(email: str, ip_address: str) -> str:
    digest = hashlib.sha256(f"{email}|{ip_address}".encode()).hexdigest()
    return f"{get_settings().redis_prefix}:auth:login:{digest}"


async def login_is_limited(redis, email: str, ip_address: str) -> bool:
    value = await redis.get(login_failure_key(email, ip_address))
    return int(value or 0) >= 5


async def record_login_failure(redis, email: str, ip_address: str) -> None:
    key = login_failure_key(email, ip_address)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 900)


async def clear_login_failures(redis, email: str, ip_address: str) -> None:
    await redis.delete(login_failure_key(email, ip_address))
