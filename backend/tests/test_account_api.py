import uuid
from datetime import UTC, datetime, time, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import CreditLedger, GenerationTask, User, Workspace


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
                media_type="image" if entry_type in {"freeze", "consume", "refund"} else None,
                model="test-image-model"
                if entry_type in {"freeze", "consume", "refund"}
                else None,
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

    async with SessionLocal() as db:
        await db.delete(await db.get(GenerationTask, task_id))
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
        assert consumed["items"][0]["model"] == "test-image-model"
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


@pytest.mark.asyncio
async def test_generation_history_filters_ownership_and_hides_internal_data(
    override_business_user,
):
    own_image_id = uuid.uuid4()
    own_reverse_id = uuid.uuid4()
    other_task_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    other_workspace_id = uuid.uuid4()
    created_at = datetime(2099, 2, 3, 4, tzinfo=UTC)
    async with SessionLocal() as db:
        workspace = await db.scalar(
            select(Workspace).where(Workspace.user_id == override_business_user)
        )
        other_user = User(
            id=other_user_id,
            username=f"history-{other_user_id.hex[:10]}",
            email=f"history-{other_user_id.hex[:10]}@example.com",
            password_hash="unused",
        )
        other_workspace = Workspace(
            id=other_workspace_id,
            user_id=other_user_id,
            name="其他用户工作台",
        )
        tasks = [
            GenerationTask(
                id=own_image_id,
                user_id=override_business_user,
                workspace_id=workspace.id,
                node_id="history-image",
                task_type="image",
                provider="secret-provider",
                model="history-image-model",
                status="succeeded",
                prompt="生成一张海报",
                request_snapshot={
                    "size": "1:1",
                    "resolution": "2k",
                    "reference_images": ["https://secret.example/reference.png"],
                    "client_business_id": "internal-id",
                },
                pricing_snapshot={"cost": "secret"},
                charged_credits=9,
                result={
                    "type": "image",
                    "data": [{"url": "https://result.example/image.png", "asset_id": "hidden"}],
                },
                created_at=created_at,
                finished_at=created_at + timedelta(seconds=10),
            ),
            GenerationTask(
                id=own_reverse_id,
                user_id=override_business_user,
                workspace_id=workspace.id,
                node_id="history-reverse",
                task_type="video_reverse",
                provider="secret-provider",
                model="history-text-model",
                status="failed",
                prompt="分析视频镜头",
                request_snapshot={"media_url": "https://secret.example/video.mp4"},
                charged_credits=0,
                error_message="上游生成失败",
                created_at=created_at + timedelta(seconds=1),
                finished_at=created_at + timedelta(seconds=2),
            ),
            GenerationTask(
                id=other_task_id,
                user_id=other_user_id,
                workspace_id=other_workspace_id,
                node_id="history-other",
                task_type="audio",
                provider="secret-provider",
                model="other-user-model",
                status="succeeded",
                prompt="其他用户内容",
                created_at=created_at + timedelta(seconds=2),
            ),
        ]
        db.add(other_user)
        await db.flush()
        db.add(other_workspace)
        await db.flush()
        db.add_all(tasks)
        await db.commit()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            images = (
                await client.get(
                    "/api/account/generations",
                    params={"media_type": "image", "status": "succeeded"},
                )
            ).json()["data"]
            failed_text = (
                await client.get(
                    "/api/account/generations",
                    params={"media_type": "text", "status": "failed"},
                )
            ).json()["data"]
            detail_response = await client.get(f"/api/account/generations/{own_image_id}")
            other_response = await client.get(f"/api/account/generations/{other_task_id}")

        image_item = next(item for item in images["items"] if item["id"] == str(own_image_id))
        reverse_item = next(
            item for item in failed_text["items"] if item["id"] == str(own_reverse_id)
        )
        assert image_item["workspace"]["name"] == workspace.name
        assert image_item["media_type"] == "image"
        assert reverse_item["type_label"] == "视频反推"
        assert all(item["id"] != str(other_task_id) for item in images["items"])

        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["result"] == {
            "type": "image",
            "url": "https://result.example/image.png",
        }
        assert {spec["label"] for spec in detail["specs"]} == {
            "比例",
            "分辨率",
            "参考图片",
        }
        serialized = str(detail)
        assert "request_snapshot" not in detail
        assert "pricing_snapshot" not in detail
        assert "secret-provider" not in serialized
        assert "secret.example" not in serialized
        assert "internal-id" not in serialized
        assert other_response.status_code == 404
    finally:
        async with SessionLocal() as db:
            for task_id in (own_image_id, own_reverse_id, other_task_id):
                task = await db.get(GenerationTask, task_id)
                if task:
                    await db.delete(task)
            await db.flush()
            other_workspace = await db.get(Workspace, other_workspace_id)
            if other_workspace:
                await db.delete(other_workspace)
            await db.flush()
            other_user = await db.get(User, other_user_id)
            if other_user:
                await db.delete(other_user)
            await db.commit()
