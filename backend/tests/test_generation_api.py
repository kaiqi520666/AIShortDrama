import uuid

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.core.database import SessionLocal
from app.models import GenerationTask


class FakeRedis:
    async def ping(self):
        return True

    async def enqueue_job(self, _name, _task_id):
        return object()

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_create_image_generation(monkeypatch):
    async def create_fake_redis_pool():
        return FakeRedis()

    monkeypatch.setattr(main_module, "create_redis_pool", create_fake_redis_pool)
    async with main_module.app.router.lifespan_context(main_module.app):
        async with AsyncClient(
            transport=ASGITransport(app=main_module.app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/generations/images",
                json={
                    "node_id": "image-api-test",
                    "model": "gpt-image-2",
                    "prompt": "test image",
                    "size": "16:9",
                    "resolution": "1k",
                },
            )

    data = response.json()
    task_id = uuid.UUID(data["data"]["id"])
    try:
        assert response.status_code == 200
        assert data["code"] == 0
        assert data["data"]["status"] == "queued"
    finally:
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            if task:
                await db.delete(task)
                await db.commit()
