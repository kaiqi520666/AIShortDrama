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


IMAGE_REQUESTS = [
    {
        "node_id": "image-gpt-test",
        "model": "gpt-image-2",
        "prompt": "test image",
        "size": "16:9",
        "resolution": "1k",
        "response_format": "url",
    },
    {
        "node_id": "image-seedream-pro-test",
        "model": "doubao-seedream-5-0-pro",
        "prompt": "test image",
        "size": "16:9",
        "metadata": {"resolution": "2K"},
        "image_urls": ["https://example.com/reference.png"],
    },
    {
        "node_id": "image-seedream-test",
        "model": "doubao-seedream-5-0",
        "prompt": "test image",
        "size": "9:16",
        "metadata": {"resolution": "3K"},
    },
    {
        "node_id": "image-gemini-pro-test",
        "model": "gemini-3-pro-image-preview",
        "prompt": "test image",
        "size": "4:3",
        "metadata": {"resolution": "4K", "orientation": "landscape"},
        "image_urls": [{"url": "https://example.com/reference.png"}],
    },
    {
        "node_id": "image-gemini-flash-test",
        "model": "gemini-3.1-flash-image-preview",
        "prompt": "test image",
        "size": "1:4",
        "metadata": {"resolution": "0.5K", "google_search": True, "google_image_search": True},
        "image_urls": [{"url": "https://example.com/reference.png"}],
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", IMAGE_REQUESTS, ids=[request["model"] for request in IMAGE_REQUESTS]
)
async def test_create_image_generation(monkeypatch, payload):
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
                json=payload,
            )

    data = response.json()
    task_id = uuid.UUID(data["data"]["id"])
    try:
        assert response.status_code == 200
        assert data["code"] == 0
        assert data["data"]["status"] == "queued"
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            assert task.model == payload["model"]
            expected_payload = {key: value for key, value in payload.items() if key != "node_id"}
            provider_payload = task.request_snapshot.copy()
            provider_payload.pop("client_business_id")
            assert provider_payload == expected_payload
    finally:
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            if task:
                await db.delete(task)
                await db.commit()
