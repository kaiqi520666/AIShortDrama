import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_user_id
from app.models import GenerationTask, Workspace


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
        "resolution": "1K",
    },
    {
        "node_id": "image-seedream-pro-test",
        "model": "doubao-seedream-5-0-pro",
        "prompt": "test image",
        "size": "16:9",
        "resolution": "2K",
        "reference_images": ["https://example.com/reference.png"],
    },
    {
        "node_id": "image-seedream-test",
        "model": "doubao-seedream-5-0",
        "prompt": "test image",
        "size": "9:16",
        "resolution": "3K",
    },
    {
        "node_id": "image-gemini-pro-test",
        "model": "gemini-3-pro-image-preview",
        "prompt": "test image",
        "size": "4:3",
        "resolution": "4K",
        "reference_images": ["https://example.com/reference.png"],
    },
    {
        "node_id": "image-gemini-flash-test",
        "model": "gemini-3.1-flash-image-preview",
        "prompt": "test image",
        "size": "1:4",
        "resolution": "1K",
        "reference_images": ["https://example.com/reference.png"],
        "google_search": True,
        "google_image_search": True,
    },
]

for request in IMAGE_REQUESTS:
    request["workspace_id"] = str(DEFAULT_WORKSPACE_ID)

VIDEO_REQUESTS = [
    {
        "node_id": "video-seedance-test",
        "model": "seedance-2",
        "prompt": "test video",
        "duration": 5,
        "resolution": "1080p",
        "aspect_ratio": "adaptive",
        "generate_audio": True,
        "reference_images": [],
    },
    {
        "node_id": "video-seedance-fast-test",
        "model": "seedance-2-fast",
        "prompt": "test video",
        "duration": 8,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generate_audio": False,
        "reference_images": ["https://example.com/one.png"],
    },
    {
        "node_id": "video-seedance-mini-test",
        "model": "seedance-2-mini",
        "prompt": "test video",
        "duration": 10,
        "resolution": "480p",
        "aspect_ratio": "1:1",
        "reference_images": [
            "https://example.com/one.png",
            "https://example.com/two.png",
        ],
    },
    {
        "node_id": "video-happyhorse-test",
        "model": "happyhorse-1.1",
        "prompt": "test video",
        "duration": 5,
        "resolution": "1080P",
        "aspect_ratio": "16:9",
        "reference_images": ["https://example.com/one.png"],
    },
]

for request in VIDEO_REQUESTS:
    request["workspace_id"] = str(DEFAULT_WORKSPACE_ID)


@pytest_asyncio.fixture
async def generation_user_id():
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        assert workspace
        user_id = workspace.user_id
    main_module.app.dependency_overrides[get_current_user_id] = lambda: user_id
    yield user_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", IMAGE_REQUESTS, ids=[request["model"] for request in IMAGE_REQUESTS]
)
async def test_create_image_generation(monkeypatch, payload, generation_user_id):
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
            expected_payload = {
                "model": payload["model"],
                "prompt": payload["prompt"],
                "size": payload["size"],
                "n": 1,
            }
            if payload["model"] == "gpt-image-2":
                expected_payload["resolution"] = payload["resolution"].lower()
                expected_payload["response_format"] = "url"
            else:
                expected_payload["metadata"] = {"resolution": payload["resolution"]}
                if payload.get("google_search"):
                    expected_payload["metadata"]["google_search"] = True
                if payload.get("google_image_search"):
                    expected_payload["metadata"]["google_image_search"] = True
                if payload.get("reference_images"):
                    expected_payload["image_urls"] = payload["reference_images"]
            provider_payload = task.request_snapshot.copy()
            provider_payload.pop("client_business_id")
            assert provider_payload == expected_payload
    finally:
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            if task:
                await db.delete(task)
                await db.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", VIDEO_REQUESTS, ids=[request["model"] for request in VIDEO_REQUESTS]
)
async def test_create_video_generation(monkeypatch, payload, generation_user_id):
    async def create_fake_redis_pool():
        return FakeRedis()

    monkeypatch.setattr(main_module, "create_redis_pool", create_fake_redis_pool)
    async with main_module.app.router.lifespan_context(main_module.app):
        async with AsyncClient(
            transport=ASGITransport(app=main_module.app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/generations/videos", json=payload)

    data = response.json()
    task_id = uuid.UUID(data["data"]["id"])
    try:
        assert response.status_code == 200
        assert data["code"] == 0
        assert data["data"]["task_type"] == "video"
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            assert task.model == payload["model"]
            if payload["model"] == "happyhorse-1.1":
                assert task.request_snapshot["action"] == "reference-to-video"
                assert task.request_snapshot["reference_images"] == payload["reference_images"]
                assert "generate_audio" not in task.request_snapshot
            else:
                expected = [
                    {"url": url, "role": "reference_image"}
                    for url in payload["reference_images"]
                ]
                assert task.request_snapshot.get("image_with_roles", []) == expected
                assert task.request_snapshot["generate_audio"] is payload.get(
                    "generate_audio", True
                )
    finally:
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            if task:
                await db.delete(task)
                await db.commit()
