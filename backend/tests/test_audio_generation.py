import base64
import uuid
from types import SimpleNamespace

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select

import app.main as main_module
import app.providers.volcengine_audio as provider_module
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, get_current_user_id
from app.models import Asset, GenerationTask, Workspace
from app.providers.volcengine_audio import VolcengineAudioError, VolcengineAudioProvider
from app.schemas.generation import AudioGenerationRequest
from app.services.generation_tasks import create_audio_task
from app.workers.audio_generation import run_audio_generation


class FakeRedis:
    async def ping(self):
        return True

    async def enqueue_job(self, name, task_id):
        return {"name": name, "task_id": task_id}

    async def aclose(self):
        pass


class FakeAudioProvider:
    async def synthesize(self, payload):
        assert payload["audio_config"]["format"] == "mp3"
        return {
            "code": 0,
            "url": "https://example.com/temp.mp3",
            "duration": 8.5,
        }


class FakeStorage:
    async def store_remote_audios(self, _task_id, urls, audio_format):
        assert urls == ["https://example.com/temp.mp3"]
        assert audio_format == "mp3"
        return ["https://image.nodepass.net/generations/audios/result.mp3"]

    async def store_audio_bytes(self, _task_id, data, audio_format):
        assert data == b"audio"
        assert audio_format == "mp3"
        return "https://image.nodepass.net/generations/audios/result.mp3"


def audio_request(**overrides):
    return AudioGenerationRequest(
        workspace_id=DEFAULT_WORKSPACE_ID,
        node_id="audio-test",
        prompt="生成自然的商品旁白",
        **overrides,
    )


def test_audio_schema_and_reference_rules():
    request = audio_request(reference_audios=["https://example.com/voice.mp3"])
    assert request.format == "mp3"
    assert request.sample_rate == 48000
    with pytest.raises(ValidationError):
        audio_request(
            reference_images=["https://example.com/product.png"],
            reference_audios=["https://example.com/voice.mp3"],
        )
    with pytest.raises(ValidationError):
        audio_request(speech_rate=101)
    with pytest.raises(ValidationError):
        audio_request(format="pcm")


@pytest.mark.asyncio
async def test_volcengine_audio_provider(monkeypatch):
    requests = []

    async def handler(request: httpx.Request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"code": 0, "url": "https://example.com/audio.mp3", "duration": 3.2},
        )

    monkeypatch.setattr(
        provider_module,
        "get_settings",
        lambda: SimpleNamespace(
            volcengine_speech_api_key="test-key",
            volcengine_speech_url="https://openspeech.bytedance.com/api/v3/tts/create",
        ),
    )
    provider = VolcengineAudioProvider(transport=httpx.MockTransport(handler))
    try:
        result = await provider.synthesize({"model": "seed-audio-1.0-multilingual"})
    finally:
        await provider.client.aclose()

    assert result["duration"] == 3.2
    assert requests[0].headers["X-Api-Key"] == "test-key"
    assert requests[0].headers["X-Api-Request-Id"]


@pytest.mark.asyncio
async def test_volcengine_audio_provider_rejects_business_error(monkeypatch):
    monkeypatch.setattr(
        provider_module,
        "get_settings",
        lambda: SimpleNamespace(
            volcengine_speech_api_key="test-key",
            volcengine_speech_url="https://openspeech.bytedance.com/api/v3/tts/create",
        ),
    )
    provider = VolcengineAudioProvider(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"code": 1001, "message": "参数错误"})
        )
    )
    try:
        with pytest.raises(VolcengineAudioError, match="参数错误"):
            await provider.synthesize({"model": "seed-audio-1.0-multilingual"})
    finally:
        await provider.client.aclose()


@pytest.mark.asyncio
async def test_create_audio_generation_api(monkeypatch):
    async def create_fake_redis_pool():
        return FakeRedis()

    monkeypatch.setattr(main_module, "create_redis_pool", create_fake_redis_pool)
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
    main_module.app.dependency_overrides[get_current_user_id] = lambda: workspace.user_id
    payload = {
        "workspace_id": str(DEFAULT_WORKSPACE_ID),
        "node_id": "audio-api-test",
        "model": "seed-audio-1.0-multilingual",
        "prompt": "@音频1 生成同风格旁白",
        "format": "mp3",
        "sample_rate": 48000,
        "speech_rate": 0,
        "loudness_rate": 0,
        "pitch_rate": 0,
        "reference_audios": ["https://example.com/reference.mp3"],
    }
    async with main_module.app.router.lifespan_context(main_module.app):
        async with AsyncClient(
            transport=ASGITransport(app=main_module.app), base_url="http://test"
        ) as client:
            response = await client.post("/api/generations/audios", json=payload)

    data = response.json()
    task_id = uuid.UUID(data["data"]["id"])
    try:
        assert data["code"] == 0
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            assert task.provider == "volcengine"
            assert "client_business_id" not in task.request_snapshot
            assert task.request_snapshot["references"] == [
                {"audio_url": "https://example.com/reference.mp3"}
            ]
    finally:
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, task_id)
            if task:
                await db.delete(task)
                await db.commit()


@pytest.mark.asyncio
async def test_audio_generation_flow():
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        task = await create_audio_task(db, FakeRedis(), audio_request(), workspace.user_id)
        task_id = task.id

    try:
        await run_audio_generation(
            str(task_id), provider=FakeAudioProvider(), storage=FakeStorage()
        )
        async with SessionLocal() as db:
            completed = await db.get(GenerationTask, task_id)
            asset = await db.scalar(select(Asset).where(Asset.generation_task_id == task_id))
            assert completed.status == "succeeded"
            assert completed.result["data"][0]["duration"] == 8.5
            assert asset.media_type == "audio"
            assert asset.mime_type == "audio/mpeg"
            assert asset.duration == 8.5
    finally:
        async with SessionLocal() as db:
            for asset in (
                await db.scalars(select(Asset).where(Asset.generation_task_id == task_id))
            ).all():
                await db.delete(asset)
            task = await db.get(GenerationTask, task_id)
            if task:
                await db.delete(task)
            await db.commit()


@pytest.mark.asyncio
async def test_audio_generation_base64_fallback():
    class Base64Provider:
        async def synthesize(self, _payload):
            return {"code": 0, "audio": base64.b64encode(b"audio").decode()}

    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        task = await create_audio_task(db, FakeRedis(), audio_request(), workspace.user_id)
        task_id = task.id

    try:
        await run_audio_generation(str(task_id), provider=Base64Provider(), storage=FakeStorage())
        async with SessionLocal() as db:
            completed = await db.get(GenerationTask, task_id)
            assert completed.status == "succeeded"
    finally:
        async with SessionLocal() as db:
            for asset in (
                await db.scalars(select(Asset).where(Asset.generation_task_id == task_id))
            ).all():
                await db.delete(asset)
            task = await db.get(GenerationTask, task_id)
            if task:
                await db.delete(task)
            await db.commit()
