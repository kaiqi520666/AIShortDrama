from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.services.provider_execution as execution
from app.services.provider_execution import SubmissionNeedsReview, submit_provider_task


def task(**overrides):
    values = {
        "id": "task-1",
        "worker_lease_token": "lease-1",
        "provider_response": None,
        "provider_task_id": None,
        "provider_request_id": None,
        "submission_started_at": None,
        "client_request_id": "client-1",
        "request_snapshot": {"prompt": "test"},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class Provider:
    supports_lookup = False
    supports_idempotent_submit = False

    def __init__(self, response=None):
        self.response = response or {"id": "provider-1"}
        self.submit_calls = []
        self.lookup_calls = []

    async def submit(self, payload, *, client_request_id=None):
        self.submit_calls.append((payload, client_request_id))
        return self.response

    async def lookup(self, client_request_id):
        self.lookup_calls.append(client_request_id)
        return None


@pytest.mark.asyncio
async def test_submission_intent_is_persisted_before_provider_io(monkeypatch):
    events = []
    update = AsyncMock(side_effect=lambda *args, **kwargs: events.append(("update", kwargs)) or True)
    monkeypatch.setattr(execution, "update_task", update)
    monkeypatch.setattr(execution, "persist_provider_result", AsyncMock())

    provider = Provider()
    original_submit = provider.submit

    async def submit(payload, *, client_request_id=None):
        events.append(("submit", client_request_id))
        return await original_submit(payload, client_request_id=client_request_id)

    provider.submit = submit
    current = task()
    response = await submit_provider_task(current, provider)

    assert response == {"id": "provider-1"}
    assert [event[0] for event in events] == ["update", "submit"]
    assert events[0][1]["submission_started_at"] is not None
    assert events[0][1]["worker_token"] == "lease-1"
    assert events[1][1] == "client-1"


@pytest.mark.asyncio
async def test_submission_recovers_by_lookup_without_resubmitting(monkeypatch):
    current = task(submission_started_at=SimpleNamespace())
    provider = Provider()
    provider.supports_lookup = True
    provider.lookup = AsyncMock(return_value={"id": "recovered-1", "status": "queued"})
    provider.submit = AsyncMock()
    persist = AsyncMock()
    monkeypatch.setattr(execution, "persist_provider_result", persist)

    response = await submit_provider_task(current, provider)

    assert response == {"id": "recovered-1", "status": "queued"}
    provider.lookup.assert_awaited_once_with("client-1")
    provider.submit.assert_not_awaited()
    persist.assert_awaited_once_with(current, response)


@pytest.mark.asyncio
async def test_unknown_submission_without_lookup_is_held_for_manual_review(monkeypatch):
    current = task(submission_started_at=SimpleNamespace())
    provider = Provider()
    provider.lookup = AsyncMock()
    mark_review = AsyncMock()
    monkeypatch.setattr(execution, "mark_needs_review", mark_review)

    with pytest.raises(SubmissionNeedsReview, match="上游提交结果未知"):
        await submit_provider_task(current, provider)

    provider.lookup.assert_not_awaited()
    mark_review.assert_awaited_once_with(
        "task-1",
        "上游提交结果未知，请人工核对后再处理",
        worker_token="lease-1",
    )


@pytest.mark.asyncio
async def test_missing_lookup_result_is_held_for_manual_review(monkeypatch):
    current = task(submission_started_at=SimpleNamespace())
    provider = Provider()
    provider.supports_lookup = True
    provider.lookup = AsyncMock(return_value=None)
    provider.submit = AsyncMock()
    mark_review = AsyncMock()
    monkeypatch.setattr(execution, "mark_needs_review", mark_review)

    with pytest.raises(SubmissionNeedsReview, match="上游提交结果未知"):
        await submit_provider_task(current, provider)

    provider.lookup.assert_awaited_once_with("client-1")
    provider.submit.assert_not_awaited()
    mark_review.assert_awaited_once()


@pytest.mark.asyncio
async def test_idempotent_provider_can_retry_with_the_same_client_request_id(monkeypatch):
    current = task(submission_started_at=SimpleNamespace())
    provider = Provider()
    provider.supports_idempotent_submit = True
    update = AsyncMock(return_value=True)
    persist = AsyncMock()
    monkeypatch.setattr(execution, "update_task", update)
    monkeypatch.setattr(execution, "persist_provider_result", persist)

    await submit_provider_task(current, provider)

    assert provider.submit_calls == [({"prompt": "test"}, "client-1")]
    update.assert_awaited_once()
    assert update.await_args.kwargs["submission_started_at"] is not None


@pytest.mark.asyncio
async def test_provider_result_persist_failure_becomes_manual_review(monkeypatch):
    current = task()
    provider = Provider()
    update = AsyncMock(side_effect=[True, False])
    monkeypatch.setattr(execution, "update_task", update)

    with pytest.raises(SubmissionNeedsReview, match="任务已暂停或交由其他 worker"):
        await submit_provider_task(current, provider)

    assert update.await_count == 2
    assert update.await_args_list[1].kwargs["provider_response"] == {"id": "provider-1"}


@pytest.mark.asyncio
async def test_provider_result_database_error_preserves_unknown_submission(monkeypatch):
    current = task()
    provider = Provider()
    monkeypatch.setattr(execution, "update_task", AsyncMock(
        side_effect=[True, RuntimeError("database unavailable")],
    ))

    with pytest.raises(SubmissionNeedsReview, match="上游"):
        await submit_provider_task(current, provider)

    assert len(provider.submit_calls) == 1
    assert current.submission_started_at is not None
    assert current.provider_response is None


@pytest.mark.asyncio
async def test_cached_provider_response_is_replayed_without_provider_io(monkeypatch):
    current = task(provider_response={"id": "cached-1", "status": "completed"})
    provider = Provider()
    provider.submit = AsyncMock()
    provider.lookup = AsyncMock()
    monkeypatch.setattr(execution, "update_task", AsyncMock())
    monkeypatch.setattr(execution, "persist_provider_result", AsyncMock())

    response = await submit_provider_task(current, provider)

    assert response == {"id": "cached-1", "status": "completed"}
    provider.submit.assert_not_awaited()
    provider.lookup.assert_not_awaited()
