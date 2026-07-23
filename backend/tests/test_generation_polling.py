import uuid

import pytest

import app.workers.generation as generation_worker
from app.providers.toapis import ToApisError


@pytest.fixture(autouse=True)
def ignore_progress_updates(monkeypatch):
    async def update_task(*_args, **_kwargs):
        pass

    monkeypatch.setattr(generation_worker, "update_task", update_task)


@pytest.mark.asyncio
async def test_poll_generation_retries_temporary_query_error():
    calls = 0

    async def fetch_task(_task_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ToApisError("temporary", retryable=True)
        return {"status": "completed", "progress": 100, "result": {"data": [{"url": "ok"}]}}

    result = await generation_worker.poll_generation(
        fetch_task, "provider-task", uuid.uuid4(), "视频", 0, 2
    )
    assert result["status"] == "completed"
    assert calls == 2


@pytest.mark.asyncio
async def test_poll_generation_reports_failure():
    async def fetch_task(_task_id):
        return {"status": "failed", "error": {"message": "blocked"}}

    with pytest.raises(ToApisError, match="blocked"):
        await generation_worker.poll_generation(
            fetch_task, "provider-task", uuid.uuid4(), "视频", 0, 1
        )


@pytest.mark.asyncio
async def test_poll_generation_times_out():
    async def fetch_task(_task_id):
        return {"status": "in_progress", "progress": 20}

    with pytest.raises(generation_worker.GenerationPollTimeout, match="视频生成超时"):
        await generation_worker.poll_generation(
            fetch_task, "provider-task", uuid.uuid4(), "视频", 0, 1
        )


def test_result_urls_requires_video_url():
    with pytest.raises(ToApisError, match="未返回视频地址"):
        generation_worker.result_urls({"status": "completed", "result": None}, "视频")
