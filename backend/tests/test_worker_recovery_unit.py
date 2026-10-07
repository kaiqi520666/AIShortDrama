import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from arq import Retry

import app.workers.audio_generation as audio_worker
import app.workers.generation as worker
import app.workers.image_generation as image_worker
import app.workers.video_generation as video_worker
from app.services.provider_execution import SubmissionNeedsReview
from app.providers.toapis import ToApisError


def current_task(**overrides):
    values = {
        "id": uuid.uuid4(),
        "provider": "test",
        "provider_task_id": None,
        "provider_response": None,
        "worker_lease_token": "worker-lease-1",
        "submission_started_at": None,
        "request_snapshot": {"audio_config": {"format": "mp3"}},
        "recovery_attempts": 0,
        "status": "queued",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class MockSession:
    def __init__(self, task):
        self.get = AsyncMock(return_value=task)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize("throws", [False, True])
async def test_queued_worker_requests_arq_retry_after_queue_recovery(monkeypatch, throws):
    task = current_task()
    session = MockSession(task)
    monkeypatch.setattr(worker, "SessionLocal", lambda: session)
    run = AsyncMock(side_effect=RuntimeError("temporary failure") if throws else None)

    with pytest.raises(Retry):
        await worker.run_queued_worker(run, str(task.id))

    run.assert_awaited_once_with(str(task.id))
    session.get.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["succeeded", "failed", "needs_review"])
async def test_queued_worker_does_not_retry_resolved_or_manual_review_task(monkeypatch, status):
    task = current_task(status=status)
    session = MockSession(task)
    monkeypatch.setattr(worker, "SessionLocal", lambda: session)

    await worker.run_queued_worker(AsyncMock(), str(task.id))
    with pytest.raises(RuntimeError, match="original failure"):
        await worker.run_queued_worker(
            AsyncMock(side_effect=RuntimeError("original failure")), str(task.id)
        )


@pytest.mark.asyncio
async def test_queued_worker_respects_automatic_recovery_limit(monkeypatch):
    task = current_task(recovery_attempts=worker.MAX_RECOVERY_ATTEMPTS)
    monkeypatch.setattr(worker, "SessionLocal", lambda: MockSession(task))

    await worker.run_queued_worker(AsyncMock(), str(task.id))
    with pytest.raises(RuntimeError, match="original failure"):
        await worker.run_queued_worker(
            AsyncMock(side_effect=RuntimeError("original failure")), str(task.id)
        )


def mock_media_lifecycle(monkeypatch, media_module, task):
    provider = SimpleNamespace(aclose=AsyncMock())
    mocks = {
        "start_task": AsyncMock(return_value=task),
        "mark_needs_review": AsyncMock(),
        "queue_task": AsyncMock(),
        "fail_task": AsyncMock(),
        "complete_task": AsyncMock(),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(media_module, name, mock)
    monkeypatch.setattr(media_module, "create_generation_provider", lambda *_args: provider)
    return provider, mocks


@pytest.mark.asyncio
@pytest.mark.parametrize("media_module", [image_worker, video_worker], ids=["image", "video"])
async def test_media_submission_result_persist_failure_only_marks_review(
    monkeypatch, media_module
):
    task = current_task(submission_started_at=SimpleNamespace())
    provider, lifecycle = mock_media_lifecycle(monkeypatch, media_module, task)
    submit = AsyncMock(
        side_effect=SubmissionNeedsReview("上游已接受请求，但本地无法保存结果，请人工核查")
    )
    monkeypatch.setattr(media_module, "submit_provider_task", submit)
    storage = SimpleNamespace(
        store_remote_images=AsyncMock(), store_remote_videos=AsyncMock()
    )
    run = (
        media_module.run_image_generation
        if media_module is image_worker
        else media_module.run_video_generation
    )

    await run(str(task.id), storage=storage)

    lifecycle["mark_needs_review"].assert_awaited_once()
    assert lifecycle["mark_needs_review"].await_args.kwargs["worker_token"] == "worker-lease-1"
    lifecycle["fail_task"].assert_not_awaited()
    lifecycle["queue_task"].assert_not_awaited()
    lifecycle["complete_task"].assert_not_awaited()
    storage.store_remote_images.assert_not_awaited()
    storage.store_remote_videos.assert_not_awaited()
    provider.aclose.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("media_module", [image_worker, video_worker], ids=["image", "video"])
async def test_media_storage_failure_keeps_credits_and_queues_retry(monkeypatch, media_module):
    task = current_task(submission_started_at=SimpleNamespace())
    provider, lifecycle = mock_media_lifecycle(monkeypatch, media_module, task)
    state = {
        "id": "provider-task-1",
        "status": "completed",
        "result": {"data": [{"url": "https://example.invalid/result"}]},
    }
    monkeypatch.setattr(media_module, "submit_provider_task", AsyncMock(return_value=state))
    persist = AsyncMock()
    monkeypatch.setattr(media_module, "persist_provider_result", persist)
    storage = SimpleNamespace(
        store_remote_images=AsyncMock(side_effect=RuntimeError("storage unavailable")),
        store_remote_videos=AsyncMock(side_effect=RuntimeError("storage unavailable")),
    )
    run = (
        media_module.run_image_generation
        if media_module is image_worker
        else media_module.run_video_generation
    )

    with pytest.raises(RuntimeError, match="storage unavailable"):
        await run(str(task.id), storage=storage)

    persist.assert_awaited_once_with(task, state)
    lifecycle["queue_task"].assert_awaited_once()
    assert lifecycle["queue_task"].await_args.kwargs["worker_token"] == "worker-lease-1"
    lifecycle["fail_task"].assert_not_awaited()
    lifecycle["mark_needs_review"].assert_not_awaited()
    lifecycle["complete_task"].assert_not_awaited()
    provider.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_audio_provider_factory_failure_before_submission_fails_and_refunds(monkeypatch):
    task = current_task()
    _provider, lifecycle = mock_media_lifecycle(monkeypatch, audio_worker, task)
    factory = Mock(side_effect=RuntimeError("provider configuration unavailable"))
    monkeypatch.setattr(audio_worker, "create_generation_provider", factory)
    submit = AsyncMock()
    monkeypatch.setattr(audio_worker, "submit_provider_task", submit)

    with pytest.raises(RuntimeError, match="provider configuration unavailable"):
        await audio_worker.run_audio_generation(str(task.id))

    submit.assert_not_awaited()
    assert task.submission_started_at is None
    lifecycle["fail_task"].assert_awaited_once()
    assert lifecycle["fail_task"].await_args.args[:2] == (task.id, "failed")
    assert lifecycle["fail_task"].await_args.kwargs["worker_token"] == "worker-lease-1"
    lifecycle["queue_task"].assert_not_awaited()
    lifecycle["mark_needs_review"].assert_not_awaited()
    lifecycle["complete_task"].assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("media_module", [image_worker, video_worker], ids=["image", "video"])
@pytest.mark.parametrize("error", [
    ToApisError("lookup unavailable", status_code=503, retryable=True),
    ToApisError("lookup authorization unavailable", status_code=401),
])
async def test_media_lookup_errors_recover_without_refund(monkeypatch, media_module, error):
    task = current_task(submission_started_at=SimpleNamespace())
    provider, lifecycle = mock_media_lifecycle(monkeypatch, media_module, task)
    monkeypatch.setattr(
        media_module, "submit_provider_task", AsyncMock(side_effect=error),
    )
    run = (
        media_module.run_image_generation
        if media_module is image_worker
        else media_module.run_video_generation
    )
    with pytest.raises(ToApisError):
        await run(str(task.id))
    lifecycle["queue_task"].assert_awaited_once()
    lifecycle["fail_task"].assert_not_awaited()
    lifecycle["mark_needs_review"].assert_not_awaited()
    provider.aclose.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "media_module", [image_worker, video_worker, audio_worker], ids=["image", "video", "audio"]
)
async def test_provider_factory_failure_during_recovery_keeps_credits(monkeypatch, media_module):
    task = current_task(submission_started_at=SimpleNamespace())
    _provider, lifecycle = mock_media_lifecycle(monkeypatch, media_module, task)
    monkeypatch.setattr(
        media_module, "create_generation_provider",
        Mock(side_effect=RuntimeError("provider configuration unavailable")),
    )
    run = {
        image_worker: image_worker.run_image_generation,
        video_worker: video_worker.run_video_generation,
        audio_worker: audio_worker.run_audio_generation,
    }[media_module]
    with pytest.raises(RuntimeError, match="provider configuration"):
        await run(str(task.id))
    lifecycle["queue_task"].assert_awaited_once()
    lifecycle["fail_task"].assert_not_awaited()
    lifecycle["complete_task"].assert_not_awaited()
