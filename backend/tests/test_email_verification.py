from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.providers import turnstile
from app.providers.turnstile import TurnstileVerificationError
from app.services.email_verification import (
    EmailVerificationError,
    consume_registration_code,
    issue_registration_code,
)


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, *keys):
        return sum(self.values.pop(key, None) is not None for key in keys)

    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    async def expire(self, _key, _ttl):
        return True

    async def eval(self, _script, _count, key, _window):
        return await self.incr(key)


def empty_db():
    return SimpleNamespace(scalar=AsyncMock(return_value=None))


@pytest.mark.asyncio
async def test_registration_code_is_hashed_and_consumed_once():
    redis = FakeRedis()
    sender = AsyncMock()
    captcha = AsyncMock()

    await issue_registration_code(
        empty_db(),
        redis,
        " User@Example.com ",
        "203.0.113.8",
        "captcha-token",
        send_email=sender,
        verify_captcha=captcha,
    )

    email, code = sender.await_args.args
    assert email == "user@example.com"
    assert len(code) == 6 and code.isdigit()
    assert code not in redis.values.values()
    captcha.assert_awaited_once_with("captcha-token", "203.0.113.8", "register_email")

    await consume_registration_code(redis, email, code)
    with pytest.raises(EmailVerificationError, match="已过期"):
        await consume_registration_code(redis, email, code)


@pytest.mark.asyncio
async def test_registration_code_rejects_captcha_and_cleans_up_send_failure():
    redis = FakeRedis()
    with pytest.raises(EmailVerificationError, match="重新完成人机验证"):
        await issue_registration_code(
            empty_db(),
            redis,
            "user@example.com",
            "203.0.113.8",
            "invalid",
            verify_captcha=AsyncMock(
                side_effect=TurnstileVerificationError("请重新完成人机验证")
            ),
        )

    with pytest.raises(EmailVerificationError, match="邮件发送失败"):
        await issue_registration_code(
            empty_db(),
            redis,
            "user@example.com",
            "203.0.113.8",
            "valid",
            verify_captcha=AsyncMock(),
            send_email=AsyncMock(side_effect=RuntimeError("offline")),
        )
    assert not any("value" in key or "cooldown" in key for key in redis.values)


def client_context(client):
    context = AsyncMock()
    context.__aenter__.return_value = client
    return context


@pytest.mark.asyncio
async def test_turnstile_requires_matching_action(monkeypatch):
    monkeypatch.setattr(
        turnstile,
        "get_settings",
        lambda: SimpleNamespace(turnstile_secret_key="test-secret"),
    )
    response = Mock()
    response.json.return_value = {"success": True, "action": "register_email"}
    client = AsyncMock()
    client.post.return_value = response

    with patch("app.providers.turnstile.httpx.AsyncClient", return_value=client_context(client)):
        await turnstile.verify_turnstile("token", "203.0.113.8", "register_email")
        with pytest.raises(TurnstileVerificationError, match="重新完成人机验证"):
            await turnstile.verify_turnstile("token", "203.0.113.8", "login")
