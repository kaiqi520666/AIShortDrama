import asyncio
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    create_refresh_session,
    decode_token,
    hash_password,
    revoke_refresh_session,
    rotate_refresh_session,
    set_auth_cookies,
    verify_password,
)
from app.core.client_ip import client_ip
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import RequestError, ServiceUnavailableError
from app.core.identity import get_current_user
from app.models import User
from app.schemas.auth import ChangePasswordRequest, EmailCodeRequest, LoginRequest, RegisterRequest
from app.schemas.response import fail, success
from app.services.authentication import RegistrationError, register_user, user_payload
from app.services.email_verification import (
    COOLDOWN_SECONDS,
    EmailVerificationError,
    consume_registration_code,
    issue_registration_code,
)
from app.services.login_security import (
    LoginSecurityState,
    clear_login_failures,
    get_login_security_state,
    record_login_failure,
)
from app.providers.turnstile import TurnstileVerificationError, verify_turnstile

router = APIRouter()
DUMMY_PASSWORD_HASH = hash_password("invalid-password-placeholder")


def unauthorized(message: str) -> JSONResponse:
    response = JSONResponse(status_code=401, content=fail(message, error_key="unauthorized"))
    clear_auth_cookies(response)
    return response


def login_security_payload(state: LoginSecurityState) -> dict:
    data = {"captcha_required": state.captcha_required}
    if state.retry_after_seconds is not None:
        data["retry_after_seconds"] = state.retry_after_seconds
    return data


@router.get("/captcha-config")
async def captcha_config():
    site_key = get_settings().turnstile_site_key
    if not site_key:
        raise ServiceUnavailableError("人机验证未配置")
    return success({"site_key": site_key})


@router.post("/email-code")
async def send_email_code(
    payload: EmailCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        await issue_registration_code(
            db,
            request.app.state.redis,
            str(payload.email),
            client_ip(request),
            payload.captcha_token,
        )
    except EmailVerificationError as exc:
        raise RequestError(str(exc)) from exc
    return success({"cooldown_seconds": COOLDOWN_SECONDS}, "验证码已发送")


@router.post("/register")
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = str(payload.email).casefold()
    duplicate = await db.scalar(
        select(User.id).where(
            (User.username == payload.username) | (User.email == email)
        ).limit(1)
    )
    if duplicate:
        raise RequestError("用户名或邮箱已注册", error_key="account_exists")
    try:
        await consume_registration_code(
            request.app.state.redis,
            email,
            payload.verification_code,
        )
    except EmailVerificationError as exc:
        raise RequestError(str(exc)) from exc
    encoded_password = await asyncio.to_thread(hash_password, payload.password)
    try:
        user = await register_user(
            db,
            username=payload.username,
            email=email,
            encoded_password=encoded_password,
        )
    except RegistrationError as exc:
        raise RequestError(str(exc)) from exc
    access_token, refresh_token = await create_refresh_session(
        request.app.state.redis,
        user.id,
        user.auth_version,
    )
    set_auth_cookies(response, access_token, refresh_token)
    return success(user_payload(user))


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = str(payload.email).casefold()
    ip_address = client_ip(request)
    redis = request.app.state.redis
    security = await get_login_security_state(redis, email, ip_address)
    if security.rate_limited:
        return JSONResponse(
            status_code=429,
            content=fail("登录尝试过于频繁，请稍后再试", login_security_payload(security), error_key="rate_limited"),
        )
    if security.captcha_required:
        try:
            await verify_turnstile(payload.captcha_token or "", ip_address, "login")
        except TurnstileVerificationError as exc:
            return JSONResponse(
                status_code=401,
                content=fail(str(exc), login_security_payload(security), error_key="captcha_failed"),
            )

    user = await db.scalar(
        select(User).where(User.email == email, User.is_system.is_(False))
    )
    valid = await asyncio.to_thread(
        verify_password,
        payload.password,
        user.password_hash if user else DUMMY_PASSWORD_HASH,
    )
    if not user or not valid:
        security = await record_login_failure(redis, email, ip_address)
        message = "登录尝试过于频繁，请稍后再试" if security.rate_limited else "邮箱或密码错误"
        return JSONResponse(
            status_code=429 if security.rate_limited else 401,
            content=fail(message, login_security_payload(security), error_key="rate_limited" if security.rate_limited else "invalid_credentials"),
        )
    if user.status != "active":
        return JSONResponse(status_code=403, content=fail("账号已被禁用", error_key="account_disabled"))

    await clear_login_failures(redis, email, ip_address)
    access_token, refresh_token = await create_refresh_session(
        redis,
        user.id,
        user.auth_version,
    )
    set_auth_cookies(response, access_token, refresh_token)
    return success(user_payload(user))


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        return unauthorized("登录状态已失效")
    try:
        claims = decode_token(token, "refresh")
        user_id = uuid.UUID(claims["sub"])
    except Exception:
        return unauthorized("登录状态已失效")

    tokens = await rotate_refresh_session(request.app.state.redis, claims)
    if not tokens:
        return unauthorized("登录状态已失效")
    user = await db.get(User, user_id)
    if (
        not user
        or user.is_system
        or user.status != "active"
        or user.auth_version != int(claims["ver"])
    ):
        await revoke_refresh_session(request.app.state.redis, claims["sid"])
        return unauthorized("登录状态已失效")

    set_auth_cookies(response, *tokens)
    return success(user_payload(user))


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            claims = decode_token(token, "refresh")
            await revoke_refresh_session(request.app.state.redis, claims["sid"])
        except Exception:
            pass
    clear_auth_cookies(response)
    return success(None)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    current = await db.scalar(select(User).where(User.id == user.id).with_for_update())
    if not await asyncio.to_thread(verify_password, payload.current_password, current.password_hash):
        raise RequestError("原密码错误", error_key="incorrect_password")
    if payload.current_password == payload.new_password:
        raise RequestError("新密码不能与原密码相同", error_key="password_unchanged")

    current.password_hash = await asyncio.to_thread(hash_password, payload.new_password)
    current.auth_version += 1
    tokens = await create_refresh_session(
        request.app.state.redis,
        current.id,
        current.auth_version,
    )
    await db.commit()
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            await revoke_refresh_session(
                request.app.state.redis,
                decode_token(token, "refresh")["sid"],
            )
        except Exception:
            pass
    set_auth_cookies(response, *tokens)
    return success(user_payload(current))


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return success(user_payload(user))
