import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import generations as generations_route
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import GenerationTask


class FakeProvider:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def stream_text(self, **_kwargs):
        yield "轻盈防风，"
        yield "自在出发。"


@pytest.mark.asyncio
async def test_stream_text_generation(monkeypatch):
    monkeypatch.setattr(generations_route, "DashScopeProvider", FakeProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/generations/texts",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "selling-copy-test",
                "model": "qwen3.7-plus",
                "prompt": "为轻量冲锋衣生成核心卖点",
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    task_id = uuid.UUID(events[0]["task_id"])
    assert events[1:] == [
        {"type": "delta", "content": "轻盈防风，"},
        {"type": "delta", "content": "自在出发。"},
        {"type": "done"},
    ]
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.task_type == "text"
        assert task.status == "succeeded"
        assert task.result == {"type": "text", "content": "轻盈防风，自在出发。"}
        await db.delete(task)
        await db.commit()


@pytest.mark.asyncio
async def test_text_generation_rejects_blank_prompt():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/generations/texts",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "selling-copy-test",
                "model": "qwen3.7-plus",
                "prompt": "   ",
            },
        )

    assert response.status_code == 422
