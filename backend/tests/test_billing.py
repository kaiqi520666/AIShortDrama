import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.models import CreditLedger, GenerationTask, User, Workspace
from app.schemas.generation import ImageGenerationRequest
from app.services.billing import (
    InsufficientCredits,
    build_price_snapshot,
    freeze_task_credits,
    refund_task_credits,
    settle_task_credits,
)
from app.services.generation_tasks import create_image_task
from app.workers.generation import compensate_stale_generation_tasks


class FakeRedis:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds

    async def enqueue_job(self, *_args):
        return object() if self.succeeds else None


async def owner_id():
    async with SessionLocal() as db:
        return (await db.get(Workspace, DEFAULT_WORKSPACE_ID)).user_id


@pytest.mark.asyncio
async def test_model_price_calculation():
    async with SessionLocal() as db:
        image_prices = [
            ("gpt-image-2", "1K", 3),
            ("gpt-image-2", "2K", 4),
            ("gpt-image-2", "4K", 5),
            ("doubao-seedream-5-0-pro", "2K", 9),
            ("doubao-seedream-5-0", "2K", 7),
            ("gemini-3-pro-image-preview", "1K", 12),
            ("gemini-3.1-flash-image-preview", "1K", 6),
        ]
        for model, resolution, expected in image_prices:
            snapshot = await build_price_snapshot(db, "image", model, resolution=resolution)
            assert snapshot["frozen_credits"] == expected
        for model, expected in [
            ("seedance-2", 26),
            ("seedance-2-fast", 21),
            ("seedance-2-mini", 15),
        ]:
            assert (await build_price_snapshot(db, "video", model, duration=1))[
                "frozen_credits"
            ] == expected
        for model in ("qwen3.7-plus", "qwen3.6-flash"):
            assert (await build_price_snapshot(db, "text", model))["frozen_credits"] == 1
        assert (await build_price_snapshot(db, "audio", "seed-audio-1.0-multilingual"))[
            "frozen_credits"
        ] == 60


@pytest.mark.asyncio
async def test_audio_settlement_refunds_difference_once():
    user_id = await owner_id()
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        initial_balance = user.credit_balance
        task = GenerationTask(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-audio",
            task_type="audio",
            provider="volcengine",
            model="seed-audio-1.0-multilingual",
        )
        db.add(task)
        await freeze_task_credits(db, task, "audio")
        await db.commit()
        await settle_task_credits(db, task, original_duration=30)
        await db.commit()
        await settle_task_credits(db, task, original_duration=30)
        await db.commit()

        await db.refresh(task)
        await db.refresh(user)
        entries = list(
            await db.scalars(select(CreditLedger).where(CreditLedger.task_id == task.id))
        )
        assert task.charged_credits == 15
        assert task.credit_status == "consumed"
        assert user.credit_balance == initial_balance - 15
        assert user.credit_frozen == 0
        assert [entry.entry_type for entry in entries] == ["freeze", "consume", "refund"]
        await db.delete(task)
        await db.commit()


@pytest.mark.asyncio
async def test_insufficient_and_concurrent_freeze():
    user_id = await owner_id()
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        user.credit_balance = 3
        await db.commit()

    async def create(node_id):
        async with SessionLocal() as db:
            request = ImageGenerationRequest(
                workspace_id=DEFAULT_WORKSPACE_ID,
                node_id=node_id,
                model="gpt-image-2",
                prompt="test",
            )
            try:
                return await create_image_task(db, FakeRedis(), request, user_id)
            except InsufficientCredits:
                return None

    tasks = await asyncio.gather(create("billing-concurrent-1"), create("billing-concurrent-2"))
    assert sum(task is not None for task in tasks) == 1
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        assert (user.credit_balance, user.credit_frozen) == (0, 3)
        for task in tasks:
            if task:
                await refund_task_credits(db, task, "测试退款")
                await db.delete(await db.get(GenerationTask, task.id))
        await db.commit()


@pytest.mark.asyncio
async def test_enqueue_failure_refunds_frozen_credits():
    user_id = await owner_id()
    async with SessionLocal() as db:
        initial_balance = (await db.get(User, user_id)).credit_balance
        request = ImageGenerationRequest(
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-enqueue-failure",
            model="gpt-image-2",
            prompt="test",
        )
        with pytest.raises(RuntimeError, match="任务入队失败"):
            await create_image_task(db, FakeRedis(False), request, user_id)

        task = await db.scalar(
            select(GenerationTask).where(GenerationTask.node_id == "billing-enqueue-failure")
        )
        user = await db.get(User, user_id)
        assert task.status == "failed"
        assert task.credit_status == "refunded"
        assert (user.credit_balance, user.credit_frozen) == (initial_balance, 0)
        await db.delete(task)
        await db.commit()


@pytest.mark.asyncio
async def test_stale_task_compensation_refunds_once():
    user_id = await owner_id()
    async with SessionLocal() as db:
        initial_balance = (await db.get(User, user_id)).credit_balance
        task = GenerationTask(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-timeout",
            task_type="image",
            provider="toapis",
            model="gpt-image-2",
            created_at=datetime.now(UTC) - timedelta(minutes=31),
        )
        db.add(task)
        await freeze_task_credits(db, task, "image", resolution="1K")
        await db.commit()

    await compensate_stale_generation_tasks(None)
    await compensate_stale_generation_tasks(None)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task.id)
        user = await db.get(User, user_id)
        assert (task.status, task.credit_status) == ("timeout", "refunded")
        assert (user.credit_balance, user.credit_frozen) == (initial_balance, 0)
        await db.delete(task)
        await db.commit()
