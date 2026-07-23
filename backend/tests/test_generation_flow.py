import uuid

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.models import Asset, GenerationTask, Workspace
from app.schemas.generation import ImageGenerationRequest, VideoGenerationRequest
from app.services.generation_tasks import create_image_task, create_video_task
from app.workers.image_generation import run_image_generation
from app.workers.video_generation import run_video_generation


class FakeRedis:
    async def enqueue_job(self, name, task_id):
        return {"name": name, "task_id": task_id}


class FakeProvider:
    async def submit_image(self, payload):
        assert payload["client_business_id"]
        return {"id": "provider-task-1", "status": "queued"}

    async def get_image_task(self, _task_id):
        return {
            "status": "completed",
            "progress": 100,
            "result": {"type": "image", "data": [{"url": "https://example.com/temp.png"}]},
        }


class FakeStorage:
    async def store_remote_images(self, _task_id, urls):
        assert urls == ["https://example.com/temp.png"]
        return ["https://image.nodepass.net/generations/images/result.png"]

    async def store_remote_videos(self, _task_id, urls):
        assert urls == ["https://example.com/temp.mp4"]
        return ["https://image.nodepass.net/generations/videos/result.mp4"]


class FakeVideoProvider:
    async def submit_video(self, payload):
        assert payload["client_business_id"]
        return {"id": "provider-video-task-1", "status": "queued"}

    async def get_video_task(self, _task_id):
        return {
            "status": "completed",
            "progress": 100,
            "result": {"type": "video", "data": [{"url": "https://example.com/temp.mp4"}]},
        }


async def default_workspace_owner():
    async with SessionLocal() as db:
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        assert workspace
        return workspace.user_id


@pytest.mark.asyncio
async def test_image_generation_flow():
    user_id = await default_workspace_owner()
    async with SessionLocal() as db:
        task = await create_image_task(
            db,
            FakeRedis(),
            ImageGenerationRequest(
                workspace_id=DEFAULT_WORKSPACE_ID,
                node_id="image-test",
                model="gpt-image-2",
                prompt="test image",
            ),
            user_id,
        )
        task_id = task.id

    try:
        await run_image_generation(
            str(task_id),
            provider=FakeProvider(),
            storage=FakeStorage(),
            poll_interval=0,
            max_polls=1,
        )
        async with SessionLocal() as db:
            completed = await db.get(GenerationTask, task_id)
            assert completed.status == "succeeded"
            assert completed.provider_task_id == "provider-task-1"
            assert completed.result["data"][0]["url"].startswith("https://image.nodepass.net/")
            assets = list(completed.id and await db.scalars(
                select(Asset).where(Asset.generation_task_id == completed.id)
            ))
            assert len(assets) == 1
    finally:
        async with SessionLocal() as db:
            for asset in (
                await db.scalars(select(Asset).where(Asset.generation_task_id == task_id))
            ).all():
                await db.delete(asset)
            task = await db.get(GenerationTask, uuid.UUID(str(task_id)))
            if task:
                await db.delete(task)
                await db.commit()


@pytest.mark.asyncio
async def test_video_generation_flow():
    user_id = await default_workspace_owner()
    async with SessionLocal() as db:
        task = await create_video_task(
            db,
            FakeRedis(),
            VideoGenerationRequest(
                workspace_id=DEFAULT_WORKSPACE_ID,
                node_id="video-test",
                model="seedance-2",
                prompt="test video",
                duration=5,
                resolution="720p",
                aspect_ratio="16:9",
                reference_images=["https://example.com/reference.png"],
            ),
            user_id,
        )
        task_id = task.id

    try:
        await run_video_generation(
            str(task_id),
            provider=FakeVideoProvider(),
            storage=FakeStorage(),
            poll_interval=0,
            max_polls=1,
        )
        async with SessionLocal() as db:
            completed = await db.get(GenerationTask, task_id)
            assert completed.status == "succeeded"
            assert completed.provider_task_id == "provider-video-task-1"
            assert completed.result["type"] == "video"
            assert completed.result["data"][0]["url"].endswith("result.mp4")
            assets = list(
                await db.scalars(select(Asset).where(Asset.generation_task_id == completed.id))
            )
            assert len(assets) == 1
            assert assets[0].media_type == "video"
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
