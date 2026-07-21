import uuid

import pytest

from app.core.database import SessionLocal
from app.models import GenerationTask
from app.schemas.generation import ImageGenerationRequest
from app.services.generation_tasks import create_image_task
from app.workers.image_generation import run_image_generation


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


@pytest.mark.asyncio
async def test_image_generation_flow():
    async with SessionLocal() as db:
        task = await create_image_task(
            db,
            FakeRedis(),
            ImageGenerationRequest(
                node_id="image-test",
                model="gpt-image-2",
                prompt="test image",
            ),
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
    finally:
        async with SessionLocal() as db:
            task = await db.get(GenerationTask, uuid.UUID(str(task_id)))
            if task:
                await db.delete(task)
                await db.commit()
