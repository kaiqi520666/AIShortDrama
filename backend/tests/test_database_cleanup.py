import uuid
from decimal import Decimal

import pytest

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


LEAK_IDS = {name: uuid.uuid4() for name in (
    "user", "workspace", "task", "asset", "character", "garment", "outfit",
    "order", "ledger", "audit", "price", "tier",
)}


@pytest.mark.asyncio
async def test_cleanup_fixture_removes_unfinalized_business_data(override_business_user):
    async with SessionLocal() as db:
        db.add(User(
            id=LEAK_IDS["user"],
            username="cleanup-leak-user",
            email="cleanup-leak@example.com",
            password_hash="test",
        ))
        await db.flush()
        db.add(Workspace(
            id=LEAK_IDS["workspace"],
            user_id=LEAK_IDS["user"],
            name="cleanup workspace",
        ))
        await db.flush()
        db.add(GenerationTask(
            id=LEAK_IDS["task"],
            user_id=override_business_user,
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="cleanup-node",
            task_type="text",
            provider="test",
            model="test-model",
        ))
        await db.flush()
        db.add(Asset(
            id=LEAK_IDS["asset"],
            user_id=override_business_user,
            workspace_id=DEFAULT_WORKSPACE_ID,
            generation_task_id=LEAK_IDS["task"],
            media_type="image",
            source_type="upload",
            name="cleanup asset",
            url="https://example.com/cleanup.png",
        ))
        db.add_all([
            Character(id=LEAK_IDS["character"], user_id=override_business_user, name="cleanup character", image_url="https://example.com/character.png"),
            Garment(id=LEAK_IDS["garment"], user_id=override_business_user, name="cleanup garment", image_url="https://example.com/garment.png"),
            OutfitModel(id=LEAK_IDS["outfit"], user_id=override_business_user, name="cleanup outfit", image_url="https://example.com/outfit.png"),
        ])
        db.add(RechargeTier(
            id=LEAK_IDS["tier"], min_amount_cents=999_900, bonus_rate_bps=100
        ))
        await db.flush()
        db.add(RechargeOrder(
            id=LEAK_IDS["order"],
            user_id=override_business_user,
            tier_id=LEAK_IDS["tier"],
            out_trade_no="cleanup-fixture-order",
            amount_cents=3500,
            base_credits=1000,
            bonus_credits=0,
            total_credits=1000,
        ))
        await db.flush()
        db.add(CreditLedger(
            id=LEAK_IDS["ledger"],
            user_id=override_business_user,
            task_id=LEAK_IDS["task"],
            entry_type="freeze",
            amount=1,
            balance_after=999_999,
            frozen_after=1,
            idempotency_key="cleanup-fixture-ledger",
        ))
        db.add(AdminAuditLog(
            id=LEAK_IDS["audit"],
            admin_id=override_business_user,
            action="cleanup_test",
            target_type="test",
            target_id="cleanup",
            reason="验证统一清理",
        ))
        db.add(ModelPriceRule(
            id=LEAK_IDS["price"],
            provider="test",
            media_type="text",
            model="cleanup-model",
            specification="",
            billing_unit="request",
            base_credits=1,
            multiplier=Decimal("1"),
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_cleanup_fixture_restores_baseline_before_next_test():
    async with SessionLocal() as db:
        models = (
            User, Workspace, GenerationTask, Asset, Character, Garment, OutfitModel,
            RechargeOrder, CreditLedger, AdminAuditLog, ModelPriceRule, RechargeTier,
        )
        rows = [
            await db.get(model, LEAK_IDS[name])
            for model, name in zip(models, LEAK_IDS, strict=True)
        ]
        assert all(row is None for row in rows)
