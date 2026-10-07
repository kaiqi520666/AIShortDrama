import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import GenerationTask
from app.services import text_generation


class FakeProvider:
    chunks = ("轻盈防风，", "自在出发。")
    last_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def stream_text(self, **_kwargs):
        self.__class__.last_kwargs = _kwargs
        for chunk in self.chunks:
            yield chunk


class FailingProvider(FakeProvider):
    async def stream_text(self, **_kwargs):
        raise RuntimeError("provider secret response")
        yield ""


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["zh-CN", "id"])
async def test_stream_text_generation(monkeypatch, locale):
    monkeypatch.setattr(text_generation, "create_text_provider", FakeProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/generations/texts",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "selling-copy-test",
                "model": "gpt-5.6-sol",
                "prompt": "为轻量冲锋衣生成核心卖点",
                "locale": locale,
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    task_id = uuid.UUID(events[0]["task_id"])
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert events[0]["type"] == "meta"
    assert events[0]["generated_locale"] == locale
    assert FakeProvider.last_kwargs["locale"] == locale
    assert events[-1]["type"] == "done"
    assert "".join(event["content"] for event in events if event["type"] == "delta") == (
        "轻盈防风，自在出发。"
    )
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.task_type == "text"
        assert task.request_snapshot["locale"] == locale
        assert task.status == "succeeded"
        assert task.result == {"type": "text", "content": "轻盈防风，自在出发。"}


@pytest.mark.asyncio
async def test_text_generation_rejects_blank_prompt():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/generations/texts",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "selling-copy-test",
                "model": "gpt-5.6-sol",
                "prompt": "   ",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stream_text_generation_keeps_content_over_3000_characters(monkeypatch):
    chunks = ("甲" * 2000, "乙" * 2000)
    monkeypatch.setattr(FakeProvider, "chunks", chunks)
    monkeypatch.setattr(text_generation, "create_text_provider", FakeProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/generations/texts",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "long-text-test",
                "model": "gpt-5.6-sol",
                "prompt": "生成完整长文本",
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    task_id = uuid.UUID(events[0]["task_id"])
    assert "".join(event["content"] for event in events if event["type"] == "delta") == "".join(chunks)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.result["content"] == "".join(chunks)


@pytest.mark.asyncio
async def test_stream_text_generation_hides_provider_error(monkeypatch):
    monkeypatch.setattr(text_generation, "create_text_provider", FailingProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/generations/texts",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "text-provider-error-test",
                "model": "gpt-5.6-sol",
                "prompt": "生成测试内容",
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    task_id = uuid.UUID(events[0]["task_id"])
    assert events[-1] == {
        "type": "error", "message": "文本生成服务暂时不可用",
        "error_key": "upstream_unavailable", "error_params": {},
    }
    assert "provider secret response" not in response.text
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.error_message == "文本生成服务暂时不可用"
