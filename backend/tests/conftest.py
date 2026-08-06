import asyncio
import os
from pathlib import Path

os.environ["APP_ENV"] = "test"

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.database import SessionLocal, engine
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_user_id
from app.main import app
from app.models import User, Workspace


BACKEND_DIR = Path(__file__).resolve().parents[1]


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
        original = (user.credit_balance, user.credit_frozen, workspace.deleted_at)
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
        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
            user.credit_balance, user.credit_frozen = original[:2]
            workspace.deleted_at = original[2]
            await db.commit()
