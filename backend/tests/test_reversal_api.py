import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.routes import reversals as reversals_route
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import GenerationTask
from app.schemas.reversal import ReversePromptRequest


class FakeProvider:
    last_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def stream_reverse_prompt(self, **_kwargs):
        self.__class__.last_kwargs = _kwargs
        yield "第一段"
        yield "第二段"


def test_product_visual_plan_requires_prompt():
    payload = {
        "workspace_id": str(DEFAULT_WORKSPACE_ID),
        "node_id": "product-visual-1",
        "model": "qwen3.7-plus",
        "media_type": "image",
        "media_url": "https://example.com/product.png",
        "response_mode": "product_visual_plan",
    }
    with pytest.raises(ValidationError, match="提示词不能为空"):
        ReversePromptRequest(**payload)
    assert ReversePromptRequest(**{**payload, "prompt": "生成出图方案"}).response_mode == "product_visual_plan"


@pytest.mark.asyncio
async def test_stream_reverse_prompt(monkeypatch):
    monkeypatch.setattr(reversals_route, "DashScopeProvider", FakeProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/reversals/stream",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "text-reverse-test",
                "model": "qwen3.7-plus",
                "media_type": "image",
                "media_url": "https://example.com/image.png",
                "prompt": "",
                "response_mode": "product_profile",
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["type"] == "meta"
    task_id = uuid.UUID(events[0]["task_id"])
    assert events[1:] == [
        {"type": "delta", "content": "第一段"},
        {"type": "delta", "content": "第二段"},
        {"type": "done"},
    ]
    assert FakeProvider.last_kwargs["response_mode"] == "product_profile"
    assert FakeProvider.last_kwargs["prompt"] == ""
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.status == "succeeded"
        assert task.result["content"] == "第一段第二段"
        await db.delete(task)
        await db.commit()
