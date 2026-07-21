import pytest_asyncio

from app.core.database import engine


@pytest_asyncio.fixture(autouse=True)
async def dispose_database_pool():
    yield
    await engine.dispose()
