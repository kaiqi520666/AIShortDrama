import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.models import (
    AdminAuditLog,
    Asset,
    Character,
    CreditLedger,
    Garment,
    GenerationTask,
    ModelPriceRule,
    OutfitModel,
    RechargeOrder,
    RechargeTier,
    User,
    Workspace,
)
from tests.conftest import BASELINE_MODELS, baseline_rows, restore_test_data, row_snapshot


@pytest.mark.asyncio
async def test_restore_test_data_removes_leaks_and_restores_baseline(
    override_business_user,
):
    leak_ids = {
        name: uuid.uuid4()
        for name in (
            "user",
            "workspace",
            "task",
            "asset",
            "character",
            "garment",
            "outfit",
            "order",
            "ledger",
            "audit",
            "price",
            "tier",
        )
    }
    async with SessionLocal() as db:
        default_workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        default_user = await db.get(User, default_workspace.user_id)
        default_user.credit_balance = 7
        default_workspace.name = "被测试污染的工作台"
        baseline_price = await db.scalar(select(ModelPriceRule).limit(1))
        baseline_tier = await db.scalar(select(RechargeTier).limit(1))
        baseline_price.multiplier = Decimal("9")
        baseline_tier.bonus_rate_bps += 99

        db.add(
            User(
                id=leak_ids["user"],
                username="cleanup-leak-user",
                email="cleanup-leak@example.com",
                password_hash="test",
            )
        )
        await db.flush()
        db.add(
            Workspace(
                id=leak_ids["workspace"],
                user_id=leak_ids["user"],
                name="cleanup workspace",
            )
        )
        await db.flush()
        db.add(
            GenerationTask(
                id=leak_ids["task"],
                user_id=override_business_user,
                workspace_id=DEFAULT_WORKSPACE_ID,
                node_id="cleanup-node",
                task_type="text",
                provider="test",
                model="test-model",
            )
        )
        await db.flush()
        db.add(
            Asset(
                id=leak_ids["asset"],
                user_id=override_business_user,
                workspace_id=DEFAULT_WORKSPACE_ID,
                generation_task_id=leak_ids["task"],
                media_type="image",
                source_type="upload",
                name="cleanup asset",
                url="https://example.com/cleanup.png",
            )
        )
        db.add_all(
            [
                Character(
                    id=leak_ids["character"],
                    user_id=override_business_user,
                    name="cleanup character",
                    image_url="https://example.com/character.png",
                ),
                Garment(
                    id=leak_ids["garment"],
                    user_id=override_business_user,
                    name="cleanup garment",
                    image_url="https://example.com/garment.png",
                ),
                OutfitModel(
                    id=leak_ids["outfit"],
                    user_id=override_business_user,
                    name="cleanup outfit",
                    image_url="https://example.com/outfit.png",
                ),
            ]
        )
        db.add(
            RechargeTier(
                id=leak_ids["tier"], min_amount_cents=999_900, bonus_rate_bps=100
            )
        )
        await db.flush()
        db.add(
            RechargeOrder(
                id=leak_ids["order"],
                user_id=override_business_user,
                tier_id=leak_ids["tier"],
                out_trade_no="cleanup-fixture-order",
                amount_cents=3500,
                base_credits=1000,
                bonus_credits=0,
                total_credits=1000,
            )
        )
        await db.flush()
        db.add_all(
            [
                CreditLedger(
                    id=leak_ids["ledger"],
                    user_id=override_business_user,
                    task_id=leak_ids["task"],
                    entry_type="freeze",
                    amount=1,
                    balance_after=999_999,
                    frozen_after=1,
                    idempotency_key="cleanup-fixture-ledger",
                ),
                AdminAuditLog(
                    id=leak_ids["audit"],
                    admin_id=override_business_user,
                    action="cleanup_test",
                    target_type="test",
                    target_id="cleanup",
                    reason="验证统一清理",
                ),
                ModelPriceRule(
                    id=leak_ids["price"],
                    provider="test",
                    media_type="text",
                    model="cleanup-model",
                    specification="",
                    billing_unit="request",
                    base_credits=1,
                    multiplier=Decimal("1"),
                ),
            ]
        )
        await db.commit()

    await restore_test_data()
    await restore_test_data()

    leak_models = (
        User,
        Workspace,
        GenerationTask,
        Asset,
        Character,
        Garment,
        OutfitModel,
        RechargeOrder,
        CreditLedger,
        AdminAuditLog,
        ModelPriceRule,
        RechargeTier,
    )
    async with SessionLocal() as db:
        leaked_rows = [
            await db.get(model, leak_ids[name])
            for model, name in zip(leak_models, leak_ids, strict=True)
        ]
        assert all(row is None for row in leaked_rows)

        for model in BASELINE_MODELS:
            restored = {
                row.id: row_snapshot(row) for row in await db.scalars(select(model))
            }
            expected = {row["id"]: row for row in baseline_rows[model]}
            assert restored == expected
