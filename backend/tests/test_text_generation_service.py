import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.generation import TextGenerationRequest
from app.services.text_generation import PreparedTextGeneration, TextGenerationService


class FakeProvider:
    def __init__(self, chunks=("第一段", "第二段"), error=None):
        self.chunks = chunks
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def stream_text(self, **_kwargs):
        for chunk in self.chunks:
            yield chunk
        if self.error:
            raise self.error


def text_request():
    return TextGenerationRequest(
        workspace_id=uuid.uuid4(),
        node_id="text-1",
        model="gpt-5.6-sol",
        prompt="生成测试内容",
    )


@pytest.mark.asyncio
async def test_stream_text_events_complete_with_compatible_ndjson():
    complete = AsyncMock()
    failed = AsyncMock()
    task_id = uuid.uuid4()
    service = TextGenerationService(
        provider_factory=FakeProvider,
        complete_task=complete,
        fail_task_handler=failed,
    )
    prepared = PreparedTextGeneration(
        task=SimpleNamespace(id=task_id), provider=FakeProvider()
    )

    events = [
        json.loads(line)
        async for line in service.stream_text_events(prepared, text_request())
    ]

    assert events == [
        {"type": "meta", "task_id": str(task_id)},
        {"type": "delta", "content": "第一段"},
        {"type": "delta", "content": "第二段"},
        {"type": "done"},
    ]
    complete.assert_awaited_once_with(task_id, "第一段第二段")
    failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_stream_text_events_fail_task_and_emit_error():
    complete = AsyncMock()
    failed = AsyncMock()
    task_id = uuid.uuid4()
    service = TextGenerationService(
        complete_task=complete,
        fail_task_handler=failed,
    )
    prepared = PreparedTextGeneration(
        task=SimpleNamespace(id=task_id),
        provider=FakeProvider(chunks=(), error=RuntimeError("上游失败")),
    )

    events = [
        json.loads(line)
        async for line in service.stream_text_events(prepared, text_request())
    ]

    assert events[-1] == {
        "type": "error", "message": "文本生成服务暂时不可用",
        "error_key": "upstream_unavailable", "error_params": {},
    }
    failed.assert_awaited_once()
    args = failed.await_args.args
    assert args[:3] == (task_id, "failed", "文本生成服务暂时不可用")
    assert args[3] is None
    complete.assert_not_awaited()
