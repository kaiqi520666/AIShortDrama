import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.auth import hash_password, verify_password
from app.core.database import SessionLocal
from app.core.identity import LOCAL_USER_ID
from app.main import app
from app.models import User, Workspace
from app.api.routes import auth as auth_routes
from app.providers.turnstile import TurnstileVerificationError
from app.services.authentication import transfer_local_data
from app.services.login_security import get_login_security_state


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, ex=None):
        self.values[key] = value

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, *keys):
        return sum(self.values.pop(key, None) is not None for key in keys)

    async def incr(self, key):
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = value
        return value

    async def expire(self, _key, _ttl):
        return True

    async def ttl(self, key):
        return 900 if key in self.values else -2

    async def eval(self, _script, _key_count, key, *args):
        if len(args) == 1:
            return await self.incr(key)
        expected, replacement, _ttl = args
        current = self.values.get(key)
        if current is None:
            return 0
        if current != expected:
            self.values.pop(key, None)
            return -1
        self.values[key] = replacement
        return 1


@pytest.mark.asyncio
async def test_password_hash_uses_argon2():
    encoded = hash_password("password-123")
    assert encoded.startswith("$argon2")
    assert verify_password("password-123", encoded)
    assert not verify_password("wrong-password", encoded)


@pytest.mark.asyncio
async def test_login_refresh_replay_and_logout():
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(
            User(
                id=user_id,
                username=f"auth-{user_id.hex[:8]}",
                email=f"auth-{user_id.hex[:8]}@example.com",
                password_hash=hash_password("password-123"),
                is_system=False,
            )
        )
        db.add(Workspace(id=workspace_id, user_id=user_id, name="认证测试", canvas={}))
        await db.commit()

    redis = FakeRedis()
    app.state.redis = redis
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        login = await client.post(
            "/api/auth/login",
            json={"email": f"AUTH-{user_id.hex[:8]}@EXAMPLE.COM", "password": "password-123"},
        )
        assert login.status_code == 200
        assert login.json()["data"]["id"] == str(user_id)
        assert "aisd_access" in login.headers.get_list("set-cookie")[0]
        assert any("HttpOnly" in value for value in login.headers.get_list("set-cookie"))
        assert any("Path=/api;" in value for value in login.headers.get_list("set-cookie"))
        assert any("Path=/api/auth;" in value for value in login.headers.get_list("set-cookie"))

        me = await client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["data"]["username"] == f"auth-{user_id.hex[:8]}"

        old_refresh = client.cookies.get("aisd_refresh")
        refreshed = await client.post("/api/auth/refresh")
        assert refreshed.status_code == 200
        client.cookies.set("aisd_refresh", old_refresh, path="/api/auth")
        replayed = await client.post("/api/auth/refresh")
        assert replayed.status_code == 401

        logged_out = await client.post("/api/auth/logout")
        assert logged_out.status_code == 200
        assert (await client.get("/api/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_login_requires_captcha_after_three_failures_and_clears_on_success(monkeypatch):
    user_id = uuid.uuid4()
    email = f"captcha-{user_id.hex[:8]}@example.com"
    async with SessionLocal() as db:
        db.add(
            User(
                id=user_id,
                username=f"captcha-{user_id.hex[:8]}",
                email=email,
                password_hash=hash_password("password-123"),
                is_system=False,
            )
        )
        await db.commit()

    redis = FakeRedis()
    app.state.redis = redis
    ip_address = "203.0.113.8"
    monkeypatch.setattr(auth_routes, "client_ip", lambda _request: ip_address)

    async def verify_captcha(token, ip, action):
        if not token:
            raise TurnstileVerificationError("请完成人机验证")
        assert (token, ip, action) == ("captcha-token", ip_address, "login")

    monkeypatch.setattr(auth_routes, "verify_turnstile", verify_captcha)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for attempt in range(3):
            response = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "wrong-password"},
            )
            assert response.status_code == 401
            assert response.json()["data"]["captcha_required"] is (attempt == 2)

        blocked = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "password-123"},
        )
        assert blocked.status_code == 401
        assert blocked.json()["message"] == "请完成人机验证"

        logged_in = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "password-123",
                "captcha_token": "captcha-token",
            },
        )

    assert logged_in.status_code == 200
    security = await get_login_security_state(redis, email, ip_address)
    assert security.captcha_required is False


@pytest.mark.asyncio
async def test_register_creates_default_workspace_without_exposing_token(monkeypatch):
    anchor_id = uuid.uuid4()
    registered_email = f"new-{anchor_id.hex[:8]}@example.com"
    async with SessionLocal() as db:
        db.add(
            User(
                id=anchor_id,
                username=f"anchor-{anchor_id.hex[:8]}",
                email=f"anchor-{anchor_id.hex[:8]}@example.com",
                password_hash="!",
                is_system=False,
            )
        )
        await db.commit()

    app.state.redis = FakeRedis()
    monkeypatch.setattr(auth_routes, "consume_registration_code", AsyncMock())
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "NewUser",
                "email": registered_email.upper(),
                "password": "password-123",
                "verification_code": "123456",
            },
        )
    data = response.json()["data"]
    registered_id = uuid.UUID(data["id"])
    assert response.status_code == 200
    assert data["username"] == "newuser"
    assert "token" not in data
    async with SessionLocal() as db:
        workspace = await db.scalar(select(Workspace).where(Workspace.user_id == registered_id))
        assert workspace.name == "默认工作台"


@pytest.mark.asyncio
async def test_first_user_transfer_rolls_back_cleanly():
    user_id = uuid.uuid4()
    async with SessionLocal() as db:
        original_status = (await db.get(User, LOCAL_USER_ID)).status
        user = User(
            id=user_id,
            username=f"transfer-{user_id.hex[:8]}",
            email=f"transfer-{user_id.hex[:8]}@example.com",
            password_hash="!",
            is_system=False,
        )
        db.add(user)
        await db.flush()
        await transfer_local_data(db, user_id)
        transferred = await db.scalar(
            select(Workspace.id).where(Workspace.user_id == user_id).limit(1)
        )
        local_user = await db.get(User, LOCAL_USER_ID)
        assert transferred
        assert local_user.status == "disabled"
        await db.rollback()

    async with SessionLocal() as db:
        local_user = await db.get(User, LOCAL_USER_ID)
        assert local_user.status == original_status
        assert await db.get(User, user_id) is None


@pytest.mark.asyncio
async def test_cross_site_auth_request_is_rejected():
    app.state.redis = FakeRedis()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/auth/login",
            headers={"Origin": "https://attacker.example"},
            json={"email": "nobody@example.com", "password": "password-123"},
        )
    assert response.status_code == 403
    assert response.json()["message"] == "请求来源无效"


@pytest.mark.asyncio
async def test_change_password_keeps_current_device_and_revokes_others():
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    email = f"password-{user_id.hex[:8]}@example.com"
    async with SessionLocal() as db:
        db.add(
            User(
                id=user_id,
                username=f"password-{user_id.hex[:8]}",
                email=email,
                password_hash=hash_password("password-123"),
                is_system=False,
            )
        )
        db.add(Workspace(id=workspace_id, user_id=user_id, name="改密测试", canvas={}))
        await db.commit()

    app.state.redis = FakeRedis()
    first = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    second = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        for client in (first, second):
            response = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "password-123"},
            )
            assert response.status_code == 200

        wrong = await first.post(
            "/api/auth/change-password",
            json={"current_password": "wrong-password", "new_password": "password-456"},
        )
        assert wrong.status_code == 422
        assert (await first.get("/api/auth/me")).status_code == 200

        invalid = await first.post(
            "/api/auth/change-password",
            json={"current_password": "password-123", "new_password": "short"},
        )
        assert invalid.status_code == 422

        unchanged = await first.post(
            "/api/auth/change-password",
            json={"current_password": "password-123", "new_password": "password-123"},
        )
        assert unchanged.status_code == 422

        changed = await first.post(
            "/api/auth/change-password",
            json={"current_password": "password-123", "new_password": "password-456"},
        )
        assert changed.status_code == 200
        assert (await first.get("/api/auth/me")).status_code == 200
        assert (await second.get("/api/auth/me")).status_code == 401
    finally:
        await first.aclose()
        await second.aclose()
