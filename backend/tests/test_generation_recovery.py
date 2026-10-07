import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.models import Asset, CreditLedger, GenerationTask, User, Workspace
from app.providers.registry import provider_registry
from app.schemas.generation import AudioGenerationRequest, ImageGenerationRequest
from app.services.generation_tasks import create_audio_task, create_image_task
from app.services.task_lifecycle import (
    complete_task, complete_text_task, fail_task, mark_needs_review, queue_task,
    start_task, update_task,
)
from app.workers.audio_generation import run_audio_generation
from app.workers.generation import compensate_stale_generation_tasks
from app.workers.image_generation import run_image_generation


class FakeRedis:
    def __init__(self):
        self.calls = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return object()


class FakeStorage:
    async def store_remote_images(self, _task_id, urls):
        assert urls == ["https://example.com/image.png"]
        return ["https://example.com/stored.png"]

    async def store_remote_audios(self, _task_id, urls, _format):
        assert urls == ["https://example.com/audio.mp3"]
        return ["https://example.com/stored.mp3"]


class FakeProvider:
    def __init__(self):
        self.submissions = 0
        self.lookups = []
        self.closed = False

    async def submit(self, payload, *, client_request_id=None):
        assert payload["client_business_id"] == client_request_id
        self.submissions += 1
        return {"id": "recover-image", "provider_request_id": "submit-request"}

    async def get_task(self, task_id):
        assert task_id == "recover-image"
        return {
            "id": task_id, "status": "completed", "progress": 100,
            "provider_request_id": "poll-request",
            "result": {"data": [{"url": "https://example.com/image.png"}]},
        }

    async def lookup(self, client_request_id):
        self.lookups.append(client_request_id)
        return {"id": "recover-image", "status": "queued", "provider_request_id": "lookup-request"}

    async def aclose(self):
        self.closed = True


async def create_task(media_type="image"):
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        if media_type == "image":
            task = await create_image_task(
                db, FakeRedis(),
                ImageGenerationRequest(
                    workspace_id=workspace.id, node_id="recovery-image",
                    model="gpt-image-2", prompt="test",
                ),
                workspace.user_id,
            )
        else:
            task = await create_audio_task(
                db, FakeRedis(),
                AudioGenerationRequest(
                    workspace_id=workspace.id, node_id="recovery-audio", prompt="test",
                ),
                workspace.user_id,
            )
        return task.id, task.user_id


@pytest.mark.asyncio
async def test_factory_to_worker_assets_and_credits_are_idempotent(monkeypatch):
    task_id, user_id = await create_task()
    provider = FakeProvider()
    monkeypatch.setitem(provider_registry._factories, ("toapis", "image"), lambda: provider)
    await run_image_generation(str(task_id), storage=FakeStorage(), poll_interval=0, max_polls=1)
    await asyncio.gather(
        complete_task(task_id, "image", ["https://example.com/stored.png"]),
        complete_task(task_id, "image", ["https://example.com/stored.png"]),
        run_image_generation(str(task_id), storage=FakeStorage()),
    )
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        user = await db.get(User, user_id)
        assert task.status == "succeeded"
        assert task.credit_status == "consumed"
        assert task.provider_request_id == "poll-request"
        assert task.client_request_id == str(task_id)
        assert task.provider_response is None
        assert provider.submissions == 1 and provider.closed
        assert user.credit_balance == 1_000_000 - task.charged_credits
        assert user.credit_frozen == 0
        assert await db.scalar(select(func.count()).select_from(Asset).where(
            Asset.generation_task_id == task_id
        )) == 1
        assert await db.scalar(select(func.count()).select_from(CreditLedger).where(
            CreditLedger.task_id == task_id, CreditLedger.entry_type == "consume"
        )) == 1


@pytest.mark.asyncio
async def test_submit_accepted_then_local_crash_recovers_by_client_id_without_resubmit():
    task_id, _ = await create_task()
    # Crash after remote accepted the request and before storing its ID.
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        task.submission_started_at = datetime.now(UTC) - timedelta(minutes=31)
        task.worker_lease_until = datetime.now(UTC) - timedelta(minutes=1)
        task.status = "running"
        await db.commit()
    provider = FakeProvider()
    await run_image_generation(
        str(task_id), provider=provider, storage=FakeStorage(), poll_interval=0, max_polls=1,
    )
    assert provider.submissions == 0
    assert provider.lookups == [str(task_id)]
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert (task.status, task.credit_status, task.provider_task_id) == (
            "succeeded", "consumed", "recover-image",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("supports_lookup", [True, False])
async def test_uncertain_submission_never_resubmits_or_refunds(supports_lookup):
    task_id, user_id = await create_task()
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        task.submission_started_at = datetime.now(UTC)
        await db.commit()

    class UnknownProvider(FakeProvider):
        async def lookup(self, client_request_id):
            self.lookups.append(client_request_id)
            return None

    provider = UnknownProvider()
    provider.supports_lookup = supports_lookup
    await run_image_generation(str(task_id), provider=provider, storage=FakeStorage())
    await run_image_generation(str(task_id), provider=provider, storage=FakeStorage())
    await complete_task(task_id, "image", ["https://example.com/stored.png"])
    await complete_text_task(task_id, "ignored")
    await fail_task(task_id, "failed", "ignored")
    await compensate_stale_generation_tasks({"redis": FakeRedis()})
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        user = await db.get(User, user_id)
        assert task.status == "needs_review" and task.credit_status == "frozen"
        assert user.credit_frozen == task.frozen_credits
        assert provider.submissions == 0
        assert await db.scalar(select(func.count()).select_from(Asset).where(
            Asset.generation_task_id == task_id
        )) == 0


@pytest.mark.asyncio
async def test_concurrent_workers_claim_one_lease_and_stale_token_cannot_finish():
    task_id, _ = await create_task()
    claims = await asyncio.gather(start_task(task_id), start_task(task_id))
    claimed = [task for task in claims if task is not None]
    assert len(claimed) == 1
    token = claimed[0].worker_lease_token
    await mark_needs_review(task_id, "manual review", worker_token=token)
    assert await update_task(task_id, progress=90, worker_token=token) is False
    await complete_task(task_id, "image", ["https://example.com/stored.png"], worker_token=token)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.status == "needs_review"


@pytest.mark.asyncio
async def test_concurrent_failure_refunds_once():
    task_id, user_id = await create_task()
    await asyncio.gather(
        fail_task(task_id, "failed", "provider rejected"),
        fail_task(task_id, "failed", "provider rejected"),
    )
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        user = await db.get(User, user_id)
        assert (task.status, task.credit_status) == ("failed", "refunded")
        assert (user.credit_balance, user.credit_frozen) == (1_000_000, 0)
        assert await db.scalar(select(func.count()).select_from(CreditLedger).where(
            CreditLedger.task_id == task_id, CreditLedger.entry_type == "refund"
        )) == 1


@pytest.mark.asyncio
async def test_audio_stored_response_recovers_without_another_provider_call():
    task_id, _ = await create_task("audio")
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        task.submission_started_at = datetime.now(UTC)
        task.provider_response = {
            "url": "https://example.com/audio.mp3", "duration": 30,
            "original_duration": 30, "provider_request_id": "audio-response",
        }
        task.provider_request_id = "audio-response"
        await db.commit()

    class NeverSubmit:
        async def synthesize(self, _payload):
            raise AssertionError("Saved audio must not synthesize twice")

    await run_audio_generation(str(task_id), provider=NeverSubmit(), storage=FakeStorage())
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        user = await db.get(User, task.user_id)
        assert task.status == "succeeded" and task.charged_credits == 15
        assert user.credit_balance == 1_000_000 - 15 and user.credit_frozen == 0
        entries = list(await db.scalars(select(CreditLedger).where(
            CreditLedger.task_id == task_id
        )))
        assert [(entry.entry_type, entry.amount) for entry in entries] == [
            ("freeze", 60), ("consume", 15), ("refund", 45),
        ]


@pytest.mark.asyncio
async def test_stale_recovery_requeues_once_and_preserves_credits():
    task_id, _ = await create_task()
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        task.submission_started_at = datetime.now(UTC) - timedelta(minutes=31)
        task.updated_at = datetime.now(UTC) - timedelta(minutes=31)
        task.provider_task_id = "recover-image"
        task.status = "running"
        await db.commit()
    redis = FakeRedis()
    await compensate_stale_generation_tasks({"redis": redis})
    await compensate_stale_generation_tasks({"redis": redis})
    assert len(redis.calls) == 1
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.status == "queued" and task.credit_status == "frozen"
        assert task.retry_count == 1


@pytest.mark.asyncio
async def test_retry_limit_pauses_instead_of_repeating_forever():
    task_id, _ = await create_task()
    for _ in range(4):
        task = await start_task(task_id)
        assert task is not None
        await queue_task(task_id, "storage unavailable", worker_token=task.worker_lease_token)
    assert await start_task(task_id) is None
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.status == "needs_review" and task.credit_status == "frozen"
        assert task.recovery_attempts == 4
