import pytest

from app.services.login_security import get_login_security_state, record_login_failure


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    async def eval(self, _script, _key_count, key, _window):
        return await self.incr(key)

    async def ttl(self, key):
        return 900 if key in self.values else -2


@pytest.mark.asyncio
async def test_login_security_uses_email_and_ip_thresholds():
    redis = FakeRedis()
    for _ in range(3):
        email_state = await record_login_failure(redis, "user@example.com", "203.0.113.8")
    assert email_state.captcha_required is True
    assert email_state.rate_limited is False

    redis = FakeRedis()
    for index in range(10):
        ip_state = await record_login_failure(
            redis,
            f"user{index}@example.com",
            "203.0.113.8",
        )
    assert ip_state.captcha_required is True
    assert ip_state.rate_limited is False


@pytest.mark.asyncio
async def test_login_security_rate_limits_ip_after_thirty_failures():
    redis = FakeRedis()
    for index in range(30):
        await record_login_failure(redis, f"user{index}@example.com", "203.0.113.8")

    state = await get_login_security_state(redis, "other@example.com", "203.0.113.8")
    assert state.captcha_required is True
    assert state.rate_limited is True
    assert state.retry_after_seconds == 900
