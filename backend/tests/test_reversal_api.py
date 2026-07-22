import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import reversals as reversals_route
from app.main import app


class FakeProvider:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def stream_reverse_prompt(self, **_kwargs):
        yield "第一段"
        yield "第二段"


@pytest.mark.asyncio
async def test_stream_reverse_prompt(monkeypatch):
    monkeypatch.setattr(reversals_route, "DashScopeProvider", FakeProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/reversals/stream",
            json={
                "model": "qwen3.7-plus",
                "media_type": "image",
                "media_url": "https://example.com/image.png",
                "prompt": "分析图片",
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    assert events == [
        {"type": "delta", "content": "第一段"},
        {"type": "delta", "content": "第二段"},
        {"type": "done"},
    ]
