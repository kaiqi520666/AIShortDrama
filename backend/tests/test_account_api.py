import uuid
from datetime import UTC, datetime, time, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import CreditLedger, GenerationTask, Workspace


@pytest.mark.asyncio
async def test_account_credit_summary_uses_beijing_consume_boundary(override_business_user):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        before = (await client.get("/api/account")).json()["data"]

    beijing = timezone(timedelta(hours=8))
    day_start = datetime.combine(datetime.now(beijing).date(), time.min, beijing).astimezone(UTC)
    entries = [
        CreditLedger(
            id=uuid.uuid4(),
            user_id=override_business_user,
            entry_type=entry_type,
            amount=amount,
            balance_after=0,
            frozen_after=0,
            idempotency_key=f"account-test:{uuid.uuid4()}",
            created_at=created_at,
        )
        for entry_type, amount, created_at in (
            ("consume", 7, day_start - timedelta(seconds=1)),
            ("consume", 11, day_start + timedelta(seconds=1)),
            ("refund", 99, day_start + timedelta(seconds=1)),
            ("freeze", 99, day_start + timedelta(seconds=1)),
        )
    ]
    try:
        async with SessionLocal() as db:
            db.add_all(entries)
            await db.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            after = (await client.get("/api/account")).json()["data"]

        assert after["credits"]["consumed_total"] == before["credits"]["consumed_total"] + 18
        assert after["credits"]["consumed_today"] == before["credits"]["consumed_today"] + 11
        assert after["user"]["username"]
        assert after["user"]["email"]
    finally:
        async with SessionLocal() as db:
            for entry in entries:
                current = await db.get(CreditLedger, entry.id)
                if current:
                    await db.delete(current)
            await db.commit()


@pytest.mark.asyncio
async def test_credit_ledger_filters_and_signed_deltas(override_business_user):
    task_id = uuid.uuid4()
    created_at = datetime(2099, 1, 2, 4, tzinfo=UTC)
    async with SessionLocal() as db:
        workspace = await db.scalar(
            select(Workspace).where(Workspace.user_id == override_business_user)
        )
        task = GenerationTask(
            id=task_id,
            user_id=override_business_user,
            workspace_id=workspace.id,
            node_id="credit-ledger-test",
            task_type="image",
            provider="test",
            model="test-image-model",
            pricing_snapshot={"media_type": "image"},
        )
        entries = [
            CreditLedger(
                id=uuid.uuid4(),
                user_id=override_business_user,
                task_id=task_id if entry_type in {"freeze", "consume", "refund"} else None,
                entry_type=entry_type,
                amount=amount,
                balance_after=100,
                frozen_after=0,
                idempotency_key=f"credit-ledger-filter:{uuid.uuid4()}",
                note=entry_type,
                created_at=created_at + timedelta(seconds=index),
            )
            for index, (entry_type, amount) in enumerate(
                (
                    ("freeze", 99),
                    ("consume", 7),
                    ("refund", 4),
                    ("adjustment", 30),
                    ("adjustment", -5),
                    ("recharge", 40),
                )
            )
        ]
        db.add(task)
        await db.flush()
        db.add_all(entries)
        await db.commit()

    params = {
        "start_at": "2099-01-02T00:00:00+00:00",
        "end_at": "2099-01-03T00:00:00+00:00",
        "page_size": 20,
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            all_items = (await client.get("/api/account/credits", params=params)).json()[
                "data"
            ]
            consumed = (
                await client.get(
                    "/api/account/credits",
                    params={**params, "type": "consume", "media_type": "image"},
                )
            ).json()["data"]

        assert all_items["total"] == 5
        assert {item["type"] for item in all_items["items"]} == {
            "consume",
            "refund",
            "system",
            "recharge",
        }
        assert [item["delta"] for item in all_items["items"] if item["type"] == "system"] == [
            -5,
            30,
        ]
        assert consumed["total"] == 1
        assert consumed["items"][0]["delta"] == -7
        assert consumed["items"][0]["media_type"] == "image"
    finally:
        async with SessionLocal() as db:
            for entry in entries:
                current = await db.get(CreditLedger, entry.id)
                if current:
                    await db.delete(current)
            current_task = await db.get(GenerationTask, task_id)
            if current_task:
                await db.delete(current_task)
            await db.commit()
