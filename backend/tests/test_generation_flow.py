import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.models import Asset, GenerationTask, Workspace
from app.providers.toapis import ToApisError
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
        if urls == ["https://example.com/temp.png"]:
            return ["https://image.nodepass.net/generations/images/result.png"]
        assert urls == ["https://example.com/last-frame.png"]
        return ["https://image.nodepass.net/generations/images/last-frame.png"]

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
            "result": {
                "type": "video",
                "data": [{
                    "url": "https://example.com/temp.mp4",
                    "last_frame_url": "https://example.com/last-frame.png",
                }],
            },
        }


class ResumeVideoProvider:
    def __init__(self):
        self.submitted = False

    async def submit_video(self, _payload):
        self.submitted = True
        raise AssertionError("恢复任务不能重复提交")

    async def get_video_task(self, task_id):
        assert task_id == "provider-video-task-existing"
        return {
            "status": "completed",
            "progress": 100,
            "result": {"data": [{"url": "https://example.com/temp.mp4"}]},
        }


class FailingVideoProvider:
    async def submit_video(self, _payload):
        raise ToApisError(
            "完整上游错误",
            status_code=524,
            request_id="req-video-failure",
            retryable=True,
        )


class PrivacyFailingVideoProvider:
    async def submit_video(self, _payload):
        raise ToApisError(
            "The request failed because the input image 'content[1]' may contain real person.",
            status_code=400,
            request_id="req-privacy-failure",
            code="InputImage.PrivacyInformation",
            details={
                "error": {
                    "code": "InputImage.PrivacyInformation",
                    "message": "The request failed because the input image may contain real person.",
                }
            },
        )


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
        workspace = await db.get(Workspace, DEFAULT_WORKSPACE_ID)
        assert workspace.thumbnail_url == completed.result["data"][0]["url"]
        assets = list(completed.id and await db.scalars(
            select(Asset).where(Asset.generation_task_id == completed.id)
        ))
        assert len(assets) == 1
        assert completed.result["data"][0]["asset_id"] == str(assets[0].id)


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
        assert completed.result["last_frame_url"].endswith("last-frame.png")
        assets = list(
            await db.scalars(select(Asset).where(Asset.generation_task_id == completed.id))
        )
        assert len(assets) == 1
        assert assets[0].media_type == "video"


@pytest.mark.asyncio
async def test_video_generation_resumes_existing_provider_task_without_resubmitting():
    user_id = await default_workspace_owner()
    async with SessionLocal() as db:
        task = await create_video_task(
            db,
            FakeRedis(),
            VideoGenerationRequest(
                workspace_id=DEFAULT_WORKSPACE_ID,
                node_id="video-resume-test",
                model="seedance-2-mini",
                prompt="resume video",
                duration=5,
                resolution="480p",
                aspect_ratio="16:9",
            ),
            user_id,
        )
        task.provider_task_id = "provider-video-task-existing"
        task.status = "running"
        await db.commit()
        task_id = task.id

    await run_video_generation(
        str(task_id),
        provider=ResumeVideoProvider(),
        storage=FakeStorage(),
        poll_interval=0,
        max_polls=1,
    )
    async with SessionLocal() as db:
        completed = await db.get(GenerationTask, task_id)
        assert completed.status == "succeeded"
        assert completed.provider_task_id == "provider-video-task-existing"


@pytest.mark.asyncio
async def test_video_generation_hides_provider_detail_from_node():
    user_id = await default_workspace_owner()
    async with SessionLocal() as db:
        task = await create_video_task(
            db,
            FakeRedis(),
            VideoGenerationRequest(
                workspace_id=DEFAULT_WORKSPACE_ID,
                node_id="video-error-test",
                model="seedance-2-mini",
                prompt="test video",
                duration=15,
                resolution="480p",
                aspect_ratio="9:16",
            ),
            user_id,
        )
        task_id = task.id

    with pytest.raises(ToApisError, match="完整上游错误"):
        await run_video_generation(str(task_id), provider=FailingVideoProvider())
    async with SessionLocal() as db:
        failed = await db.get(GenerationTask, task_id)
        assert failed.status == "needs_review"
        assert failed.error_message == "上游提交结果未知，请人工核对后再处理"
        assert failed.diagnostic_snapshot is None


@pytest.mark.asyncio
async def test_video_generation_guides_user_to_register_real_person_reference():
    user_id = await default_workspace_owner()
    async with SessionLocal() as db:
        task = await create_video_task(
            db,
            FakeRedis(),
            VideoGenerationRequest(
                workspace_id=DEFAULT_WORKSPACE_ID,
                node_id="video-privacy-error-test",
                model="seedance-2-mini",
                prompt="test video",
                duration=15,
                resolution="480p",
                aspect_ratio="9:16",
            ),
            user_id,
        )
        task_id = task.id

    with pytest.raises(ToApisError, match="may contain real person"):
        await run_video_generation(
            str(task_id), provider=PrivacyFailingVideoProvider()
        )

    async with SessionLocal() as db:
        failed = await db.get(GenerationTask, task_id)
        assert failed.error_message == (
            "参考图片中检测到真人，请在对应图片节点顶部点击人物图标，"
            "注册为 Seedance 人物素材，审核通过后重新生成视频"
        )
        assert failed.diagnostic_snapshot == {
            "error": {
                "code": "InputImage.PrivacyInformation",
                "message": "The request failed because the input image may contain real person.",
            }
        }
