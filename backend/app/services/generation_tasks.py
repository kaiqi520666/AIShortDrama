import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import GenerationTask, Workspace
from app.schemas.generation import ImageGenerationRequest, VideoGenerationRequest


def task_payload(task: GenerationTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "workspace_id": str(task.workspace_id),
        "node_id": task.node_id,
        "task_type": task.task_type,
        "model": task.model,
        "status": task.status,
        "progress": task.progress,
        "result": task.result,
        "error_message": task.error_message,
        "created_at": _iso(task.created_at),
        "started_at": _iso(task.started_at),
        "finished_at": _iso(task.finished_at),
    }


async def create_image_task(
    db: AsyncSession,
    redis: Any,
    request: ImageGenerationRequest,
    user_id: uuid.UUID,
) -> GenerationTask:
    provider_payload = request.model_dump(
        mode="json",
        exclude={"node_id", "workspace_id"},
        exclude_none=True,
        exclude_unset=True,
    )
    return await _create_task(db, redis, request, user_id, "image", provider_payload)


async def create_video_task(
    db: AsyncSession,
    redis: Any,
    request: VideoGenerationRequest,
    user_id: uuid.UUID,
) -> GenerationTask:
    provider_payload = build_video_provider_payload(request)
    return await _create_task(db, redis, request, user_id, "video", provider_payload)


def build_video_provider_payload(request: VideoGenerationRequest) -> dict[str, Any]:
    reference_images = [str(url) for url in request.reference_images]
    provider_payload = {
        "model": request.model,
        "prompt": request.prompt,
        "duration": request.duration,
        "resolution": request.resolution,
        "aspect_ratio": request.aspect_ratio,
    }
    if request.model == "happyhorse-1.1":
        provider_payload["action"] = "reference-to-video" if reference_images else "text-to-video"
        if reference_images:
            provider_payload["reference_images"] = reference_images
    else:
        provider_payload["generate_audio"] = request.generate_audio is not False
        if reference_images:
            provider_payload["image_with_roles"] = [
                {"url": url, "role": "reference_image"} for url in reference_images
            ]
    return provider_payload


async def _create_task(
    db: AsyncSession,
    redis: Any,
    request: ImageGenerationRequest | VideoGenerationRequest,
    user_id: uuid.UUID,
    task_type: str,
    provider_payload: dict[str, Any],
) -> GenerationTask:
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == request.workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
    )
    if not workspace:
        raise RuntimeError("工作台不存在")
    task_id = uuid.uuid4()
    provider_payload["client_business_id"] = str(task_id)
    task = GenerationTask(
        id=task_id,
        user_id=user_id,
        workspace_id=request.workspace_id,
        node_id=request.node_id,
        task_type=task_type,
        provider="toapis",
        model=request.model,
        prompt=request.prompt,
        request_snapshot=provider_payload,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    try:
        job = await redis.enqueue_job(f"generate_{task_type}", str(task_id))
        if job is None:
            raise RuntimeError("任务重复入队")
    except Exception as exc:
        task.status = "failed"
        task.error_message = "任务入队失败"
        await db.commit()
        raise RuntimeError("任务入队失败") from exc
    return task


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
