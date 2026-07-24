import pytest_asyncio

from app.core.database import engine
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_user_id
from app.main import app
from app.models import User, Workspace


@pytest_asyncio.fixture(autouse=True)
async def override_business_user():
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        user = await db.get(User, workspace.user_id)
        original = (user.credit_balance, user.credit_frozen)
        user.credit_balance = 1_000_000
        user.credit_frozen = 0
        await db.commit()
        user_id = user.id
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    try:
        yield user_id
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            user.credit_balance, user.credit_frozen = original
            await db.commit()


@pytest_asyncio.fixture(autouse=True)
async def dispose_database_pool():
    yield
    await engine.dispose()
