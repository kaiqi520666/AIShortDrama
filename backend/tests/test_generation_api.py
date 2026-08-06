import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.main as main_module
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_user_id
from app.models import GenerationTask, User, Workspace


class FakeRedis:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds

    async def ping(self):
        return True

    async def enqueue_job(self, _name, _task_id):
        return object() if self.succeeds else None

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


async def post_generation(monkeypatch, path, payload, redis):
    async def create_fake_redis_pool():
        return redis

    monkeypatch.setattr(main_module, "create_redis_pool", create_fake_redis_pool)
    async with main_module.app.router.lifespan_context(main_module.app):
        async with AsyncClient(
            transport=ASGITransport(app=main_module.app),
            base_url="http://test",
        ) as client:
            return await client.post(f"/api/generations/{path}", json=payload)


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
            if payload["model"].startswith("doubao-seedream-5-0"):
                expected_payload["metadata"]["watermark"] = False
            if payload.get("google_search"):
                expected_payload["metadata"]["google_search"] = True
            if payload.get("google_image_search"):
                expected_payload["metadata"]["google_image_search"] = True
            if payload.get("reference_images"):
                expected_payload["image_urls"] = payload["reference_images"]
        provider_payload = task.request_snapshot.copy()
        provider_payload.pop("client_business_id")
        assert provider_payload == expected_payload


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
    assert response.status_code == 200
    assert data["code"] == 0
    assert data["data"]["task_type"] == "video"
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.model == payload["model"]
        expected = [
            {"url": url, "role": "reference_image"} for url in payload["reference_images"]
        ]
        assert task.request_snapshot.get("image_with_roles", []) == expected
        assert task.request_snapshot["generate_audio"] is payload.get("generate_audio", True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("images", IMAGE_REQUESTS[0]),
        ("videos", VIDEO_REQUESTS[0]),
        (
            "audios",
            {
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "audio-error-test",
                "model": "seed-audio-1.0-multilingual",
                "prompt": "test audio",
                "format": "mp3",
                "sample_rate": 48000,
            },
        ),
    ],
)
async def test_generation_requires_owned_workspace(monkeypatch, path, payload, generation_user_id):
    request = {**payload, "workspace_id": str(uuid.uuid4())}
    response = await post_generation(monkeypatch, path, request, FakeRedis())

    assert response.status_code == 404
    assert response.json() == {"code": 1, "message": "工作台不存在", "data": None}


@pytest.mark.asyncio
async def test_generation_returns_402_for_insufficient_credits(monkeypatch, generation_user_id):
    async with SessionLocal() as db:
        user = await db.get(User, generation_user_id)
        user.credit_balance = 0
        await db.commit()

    response = await post_generation(
        monkeypatch,
        "images",
        {**IMAGE_REQUESTS[0], "node_id": "insufficient-credits-api"},
        FakeRedis(),
    )

    assert response.status_code == 402
    assert response.json()["message"].startswith("积分不足")


@pytest.mark.asyncio
async def test_generation_returns_503_and_refunds_when_enqueue_fails(
    monkeypatch, generation_user_id
):
    node_id = "enqueue-failure-api"
    response = await post_generation(
        monkeypatch,
        "images",
        {**IMAGE_REQUESTS[0], "node_id": node_id},
        FakeRedis(False),
    )

    assert response.status_code == 503
    assert response.json() == {"code": 1, "message": "任务入队失败", "data": None}
    async with SessionLocal() as db:
        task = await db.scalar(select(GenerationTask).where(GenerationTask.node_id == node_id))
        user = await db.get(User, generation_user_id)
        assert (task.status, task.credit_status) == ("failed", "refunded")
        assert user.credit_frozen == 0


@pytest.mark.asyncio
async def test_generation_query_returns_404(generation_user_id):
    async with AsyncClient(
        transport=ASGITransport(app=main_module.app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/generations/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"code": 1, "message": "任务不存在", "data": None}


@pytest.mark.asyncio
async def test_generation_validation_uses_error_envelope(generation_user_id):
    async with AsyncClient(
        transport=ASGITransport(app=main_module.app), base_url="http://test"
    ) as client:
        response = await client.post("/api/generations/images", json={})

    assert response.status_code == 422
    assert response.json() == {"code": 1, "message": "请求参数无效", "data": None}
