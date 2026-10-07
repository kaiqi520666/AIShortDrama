import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.models import AdminAuditLog, CreditLedger, GenerationTask, User, Workspace
from app.schemas.generation import ImageGenerationRequest
from app.services.billing import (
    InsufficientCredits,
    build_price_snapshot,
    freeze_task_credits,
    refund_task_credits,
    settle_task_credits,
)
from app.services.generation_tasks import create_image_task
from app.services.admin import adjust_credits
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
        for model, resolution, expected in [
            ("seedance-2", "480p", 13),
            ("seedance-2", "720p", 26),
            ("seedance-2", "1080p", 65),
            ("seedance-2", "4k", 143),
            ("seedance-2-fast", "480p", 8),
            ("seedance-2-fast", "720p", 16),
            ("seedance-2-mini", "480p", 3),
            ("seedance-2-mini", "720p", 6),
        ]:
            assert (await build_price_snapshot(db, "video", model, resolution=resolution, duration=1))[
                "frozen_credits"
            ] == expected
        assert (await build_price_snapshot(db, "text", "gpt-5.6-sol"))["frozen_credits"] == 1
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


@pytest.mark.asyncio
async def test_settlement_refreshes_cached_account_and_task_before_repeating():
    user_id = await owner_id()
    task_id = uuid.uuid4()
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        initial_balance = user.credit_balance
        task = GenerationTask(
            id=task_id,
            user_id=user_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-cached-settle",
            task_type="image",
            provider="toapis",
            model="gpt-image-2",
        )
        db.add(task)
        await freeze_task_credits(db, task, "image", resolution="1K")
        await db.commit()

    async with SessionLocal() as cached_db:
        cached_user = await cached_db.get(User, user_id)
        cached_task = await cached_db.get(GenerationTask, task_id)
        async with SessionLocal() as concurrent_db:
            concurrent_user = await concurrent_db.get(User, user_id)
            concurrent_user.credit_balance += 17
            concurrent_user.credit_frozen += 11
            await concurrent_db.commit()

        await settle_task_credits(cached_db, cached_task)
        await cached_db.commit()
        await settle_task_credits(cached_db, cached_task)
        await cached_db.commit()

        assert cached_user.credit_balance == initial_balance - 3 + 17
        assert cached_user.credit_frozen == 11

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        task = await db.get(GenerationTask, task_id)
        entries = list(await db.scalars(select(CreditLedger).where(CreditLedger.task_id == task_id)))
        assert (task.credit_status, task.charged_credits) == ("consumed", 3)
        assert (user.credit_balance, user.credit_frozen) == (initial_balance - 3 + 17, 11)
        assert [entry.entry_type for entry in entries] == ["freeze", "consume"]
        assert [entry.amount for entry in entries] == [3, 3]


@pytest.mark.asyncio
async def test_refund_refreshes_cached_account_and_task_before_repeating():
    user_id = await owner_id()
    task_id = uuid.uuid4()
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        initial_balance = user.credit_balance
        task = GenerationTask(
            id=task_id,
            user_id=user_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-cached-refund",
            task_type="image",
            provider="toapis",
            model="gpt-image-2",
        )
        db.add(task)
        await freeze_task_credits(db, task, "image", resolution="1K")
        await db.commit()

    async with SessionLocal() as cached_db:
        cached_user = await cached_db.get(User, user_id)
        cached_task = await cached_db.get(GenerationTask, task_id)
        async with SessionLocal() as concurrent_db:
            concurrent_user = await concurrent_db.get(User, user_id)
            concurrent_user.credit_balance += 19
            concurrent_user.credit_frozen += 7
            await concurrent_db.commit()

        await refund_task_credits(cached_db, cached_task, "测试退款")
        await cached_db.commit()
        await refund_task_credits(cached_db, cached_task, "重复测试退款")
        await cached_db.commit()

        assert cached_user.credit_balance == initial_balance + 19
        assert cached_user.credit_frozen == 7

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        task = await db.get(GenerationTask, task_id)
        entries = list(await db.scalars(select(CreditLedger).where(CreditLedger.task_id == task_id)))
        assert (task.credit_status, task.frozen_credits) == ("refunded", 3)
        assert (user.credit_balance, user.credit_frozen) == (initial_balance + 19, 7)
        assert [entry.entry_type for entry in entries] == ["freeze", "refund"]
        assert [entry.amount for entry in entries] == [3, 3]


@pytest.mark.asyncio
async def test_concurrent_freeze_of_same_task_creates_one_ledger():
    user_id = await owner_id()
    task_id = uuid.uuid4()
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        initial_balance = user.credit_balance
        task = GenerationTask(
            id=task_id,
            user_id=user_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-concurrent-same-task",
            task_type="image",
            provider="toapis",
            model="gpt-image-2",
        )
        db.add(task)
        await db.commit()

    barrier = asyncio.Barrier(2)

    async def freeze_once():
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            assert task.credit_status == "none"
            await barrier.wait()
            await freeze_task_credits(db, task, "image", resolution="1K")
            await db.commit()

    await asyncio.gather(freeze_once(), freeze_once())

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        task = await db.get(GenerationTask, task_id)
        entries = list(await db.scalars(select(CreditLedger).where(CreditLedger.task_id == task_id)))
        assert (task.credit_status, task.frozen_credits) == ("frozen", 3)
        assert (user.credit_balance, user.credit_frozen) == (initial_balance - 3, 3)
        assert [entry.entry_type for entry in entries] == ["freeze"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_action", "repeated_action"),
    [("settle", "settle"), ("refund", "refund"), ("settle", "refund"), ("refund", "settle")],
)
async def test_cached_frozen_state_cannot_repeat_another_sessions_finalization(
    first_action, repeated_action,
):
    user_id = await owner_id()
    task_id = uuid.uuid4()
    async with SessionLocal() as db:
        initial_balance = (await db.get(User, user_id)).credit_balance
        task = GenerationTask(
            id=task_id,
            user_id=user_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-cached-finalization",
            task_type="image",
            provider="toapis",
            model="gpt-image-2",
        )
        db.add(task)
        await freeze_task_credits(db, task, "image", resolution="1K")
        await db.commit()

    async def finalize(db, task, action):
        if action == "settle":
            await settle_task_credits(db, task)
        else:
            await refund_task_credits(db, task, "测试退款")
        await db.commit()

    async with SessionLocal() as cached_db:
        cached_task = await cached_db.get(GenerationTask, task_id)
        cached_user = await cached_db.get(User, user_id)
        async with SessionLocal() as concurrent_db:
            concurrent_task = await concurrent_db.get(GenerationTask, task_id)
            await finalize(concurrent_db, concurrent_task, first_action)
        assert cached_task.credit_status == "frozen"
        assert cached_user.credit_frozen == 3
        await finalize(cached_db, cached_task, repeated_action)
        assert cached_task.credit_status == ("consumed" if first_action == "settle" else "refunded")

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        entries = list(await db.scalars(select(CreditLedger).where(CreditLedger.task_id == task_id)))
        assert user.credit_balance == initial_balance - (3 if first_action == "settle" else 0)
        assert user.credit_frozen == 0
        assert [entry.entry_type for entry in entries] == [
            "freeze", "consume" if first_action == "settle" else "refund"
        ]


@pytest.mark.asyncio
async def test_freeze_refreshes_an_account_loaded_before_concurrent_balance_update():
    user_id = await owner_id()
    task_id = uuid.uuid4()
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        initial_balance = user.credit_balance
        task = GenerationTask(
            id=task_id,
            user_id=user_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="billing-cached-freeze",
            task_type="image",
            provider="toapis",
            model="gpt-image-2",
        )
        db.add(task)
        await db.commit()

    async with SessionLocal() as cached_db:
        cached_user = await cached_db.get(User, user_id)
        cached_task = await cached_db.get(GenerationTask, task_id)
        async with SessionLocal() as concurrent_db:
            concurrent_user = await concurrent_db.get(User, user_id)
            concurrent_user.credit_balance += 13
            concurrent_user.credit_frozen += 5
            await concurrent_db.commit()
        await freeze_task_credits(cached_db, cached_task, "image", resolution="1K")
        await cached_db.commit()
        assert (cached_user.credit_balance, cached_user.credit_frozen) == (initial_balance + 10, 8)

    async with SessionLocal() as db:
        entries = list(await db.scalars(select(CreditLedger).where(CreditLedger.task_id == task_id)))
        assert len(entries) == 1
        assert entries[0].entry_type == "freeze"
        assert (entries[0].balance_after, entries[0].frozen_after) == (initial_balance + 10, 8)


@pytest.mark.asyncio
async def test_admin_credit_adjustment_refreshes_a_cached_target_account():
    admin_id = uuid.uuid4()
    target_id = uuid.uuid4()
    async with SessionLocal() as db:
        db.add_all([
            User(
                id=admin_id, username=f"billing-admin-{admin_id.hex[:8]}",
                email=f"billing-admin-{admin_id.hex[:8]}@example.com",
                password_hash="test", role="admin", is_system=False,
            ),
            User(
                id=target_id, username=f"billing-target-{target_id.hex[:8]}",
                email=f"billing-target-{target_id.hex[:8]}@example.com",
                password_hash="test", credit_balance=20, credit_frozen=2, is_system=False,
            ),
        ])
        await db.commit()

    async with SessionLocal() as cached_db:
        admin = await cached_db.get(User, admin_id)
        target = await cached_db.get(User, target_id)
        async with SessionLocal() as concurrent_db:
            concurrent_target = await concurrent_db.get(User, target_id)
            concurrent_target.credit_balance += 15
            concurrent_target.credit_frozen += 4
            await concurrent_db.commit()
        assert target.credit_balance == 20
        adjusted = await adjust_credits(
            cached_db, admin=admin, user_id=target_id, amount=3, reason="测试调整积分"
        )
        assert adjusted is target
        assert (adjusted.credit_balance, adjusted.credit_frozen) == (38, 6)

    async with SessionLocal() as db:
        entries = list(await db.scalars(select(CreditLedger).where(CreditLedger.user_id == target_id)))
        audits = list(await db.scalars(select(AdminAuditLog).where(AdminAuditLog.target_id == str(target_id))))
        assert len(entries) == len(audits) == 1
        assert (entries[0].entry_type, entries[0].amount) == ("adjustment", 3)
        assert (entries[0].balance_after, entries[0].frozen_after) == (38, 6)
        assert audits[0].before_snapshot["credit_balance"] == 35
        assert audits[0].after_snapshot["credit_balance"] == 38
