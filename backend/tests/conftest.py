import asyncio
import copy
import os
from pathlib import Path

os.environ["APP_ENV"] = "test"

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select, text

from app.core.database import SessionLocal, engine
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_user_id
from app.main import app
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


BACKEND_DIR = Path(__file__).resolve().parents[1]
BASELINE_MODELS = (
    User,
    Workspace,
    ModelPriceRule,
    RechargeTier,
    OutfitModel,
    Character,
    Garment,
)
MUTABLE_MODELS = (AdminAuditLog, CreditLedger, Asset, GenerationTask, RechargeOrder)
baseline_rows = {}


def row_snapshot(row):
    return {
        column.key: copy.deepcopy(getattr(row, column.key))
        for column in row.__table__.columns
    }


async def capture_baseline() -> None:
    async with SessionLocal() as db:
        for model in BASELINE_MODELS:
            baseline_rows[model] = [
                row_snapshot(row) for row in await db.scalars(select(model))
            ]


async def restore_test_data() -> None:
    async with SessionLocal() as db:
        for model in MUTABLE_MODELS:
            await db.execute(delete(model))
        for model in (OutfitModel, Character, Garment, Workspace, User):
            baseline_ids = [row["id"] for row in baseline_rows[model]]
            statement = delete(model)
            if baseline_ids:
                statement = statement.where(model.id.not_in(baseline_ids))
            await db.execute(statement)
        for model in (ModelPriceRule, RechargeTier):
            baseline_ids = [row["id"] for row in baseline_rows[model]]
            statement = delete(model)
            if baseline_ids:
                statement = statement.where(model.id.not_in(baseline_ids))
            await db.execute(statement)
        await db.flush()
        for model in BASELINE_MODELS:
            snapshots = baseline_rows[model]
            baseline_ids = [values["id"] for values in snapshots]
            existing = {
                row.id: row
                for row in await db.scalars(select(model).where(model.id.in_(baseline_ids)))
            }
            for values in snapshots:
                row = existing.get(values["id"])
                if not row:
                    row = model()
                    db.add(row)
                for key, value in values.items():
                    setattr(row, key, copy.deepcopy(value))
        await db.commit()


async def reset_test_schema() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    asyncio.run(reset_test_schema())
    alembic_config = Config(BACKEND_DIR / "alembic.ini")
    command.upgrade(alembic_config, "head")
    asyncio.run(capture_baseline())
    yield
    asyncio.run(engine.dispose())


@pytest_asyncio.fixture(autouse=True)
async def override_business_user():
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        if not workspace:
            raise RuntimeError("测试种子工作台不存在")
        user = await db.get(User, workspace.user_id)
        if not user:
            raise RuntimeError("测试种子用户不存在")
        user.credit_balance = 1_000_000
        user.credit_frozen = 0
        workspace.deleted_at = None
        await db.commit()
        user_id = user.id
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    try:
        yield user_id
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
        await restore_test_data()
