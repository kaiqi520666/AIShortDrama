import asyncio
import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    clear_login_failures,
    create_refresh_session,
    decode_token,
    hash_password,
    login_is_limited,
    record_login_failure,
    revoke_refresh_session,
    rotate_refresh_session,
    set_auth_cookies,
    verify_password,
)
from app.core.database import get_db
from app.core.identity import get_current_user
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.schemas.response import fail, success
from app.services.authentication import RegistrationError, register_user, user_payload

router = APIRouter()
DUMMY_PASSWORD_HASH = hash_password("invalid-password-placeholder")


def unauthorized(message: str) -> JSONResponse:
    response = JSONResponse(status_code=401, content=fail(message))
    clear_auth_cookies(response)
    return response


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register")
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    encoded_password = await asyncio.to_thread(hash_password, payload.password)
    try:
        user = await register_user(
            db,
            username=payload.username,
            email=str(payload.email),
            encoded_password=encoded_password,
        )
    except RegistrationError as exc:
        return fail(str(exc))
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
    if await login_is_limited(redis, email, ip_address):
        return JSONResponse(status_code=429, content=fail("登录尝试过于频繁，请稍后再试"))

    user = await db.scalar(
        select(User).where(User.email == email, User.is_system.is_(False))
    )
    valid = await asyncio.to_thread(
        verify_password,
        payload.password,
        user.password_hash if user else DUMMY_PASSWORD_HASH,
    )
    if not user or not valid:
        await record_login_failure(redis, email, ip_address)
        return JSONResponse(status_code=401, content=fail("邮箱或密码错误"))
    if user.status != "active":
        return JSONResponse(status_code=403, content=fail("账号已被禁用"))

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
        return JSONResponse(status_code=400, content=fail("原密码错误"))
    if payload.current_password == payload.new_password:
        return JSONResponse(status_code=400, content=fail("新密码不能与原密码相同"))

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
