from typing import Any

import pytest

from app.providers.protocols import AudioProvider, ImageVideoProvider
from app.providers.registry import (
    ProviderConfigurationError,
    adapt_generation_provider,
    provider_registry,
)


class FakeMediaProvider:
    async def submit_image(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": "image-1"}

    async def submit_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": "video-1"}

    async def get_image_task(self, task_id: str) -> dict[str, Any]:
        return {"status": "succeeded", "task_id": task_id}

    async def get_video_task(self, task_id: str) -> dict[str, Any]:
        return {"status": "succeeded", "task_id": task_id}


class FakeAudioProvider:
    async def synthesize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"audio": "ZmFrZQ==", "original_duration": 1}


class FakeLookupProvider(FakeMediaProvider):
    supports_lookup = True

    async def lookup(self, client_request_id):
        return {"status": "running", "id": client_request_id}

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_fake_provider_matches_generation_protocols():
    media: ImageVideoProvider = FakeMediaProvider()
    audio: AudioProvider = FakeAudioProvider()
    assert (await media.submit_image({"prompt": "x"}))["id"] == "image-1"
    assert (await media.get_video_task("video-1"))["status"] == "succeeded"
    assert (await audio.synthesize({}))["original_duration"] == 1


@pytest.mark.asyncio
async def test_generation_adapter_maps_media_methods_and_closes_provider():
    provider = FakeLookupProvider()
    adapted = adapt_generation_provider(provider, "video")
    assert (await adapted.submit({"prompt": "x"}))["id"] == "video-1"
    assert (await adapted.get_task("video-1"))["status"] == "succeeded"
    assert await adapted.lookup("client-1") == {"status": "running", "id": "client-1"}
    await adapted.aclose()
    assert provider.closed is True


def test_provider_registry_rejects_unsupported_media():
    with pytest.raises(ProviderConfigurationError):
        provider_registry.create_generation("volcengine", "image")
