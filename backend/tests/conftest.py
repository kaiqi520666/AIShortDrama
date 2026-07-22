import pytest_asyncio

from app.core.database import engine
from app.core.identity import LOCAL_USER_ID, get_current_user_id
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def override_business_user():
    app.dependency_overrides[get_current_user_id] = lambda: LOCAL_USER_ID
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest_asyncio.fixture(autouse=True)
async def dispose_database_pool():
    yield
    await engine.dispose()
