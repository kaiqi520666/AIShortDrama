from typing import Any

import pytest

from app.providers.protocols import AudioProvider, ImageVideoProvider


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


@pytest.mark.asyncio
async def test_fake_provider_matches_generation_protocols():
    media: ImageVideoProvider = FakeMediaProvider()
    audio: AudioProvider = FakeAudioProvider()
    assert (await media.submit_image({"prompt": "x"}))["id"] == "image-1"
    assert (await media.get_video_task("video-1"))["status"] == "succeeded"
    assert (await audio.synthesize({}))["original_duration"] == 1
