import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationTask, Workspace
from app.schemas.generation import (
    AudioGenerationRequest,
    ImageGenerationRequest,
    VideoGenerationRequest,
)
from app.services.billing import freeze_task_credits, refund_task_credits


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
        "frozen_credits": task.frozen_credits,
        "charged_credits": task.charged_credits,
        "credit_status": task.credit_status,
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
    provider_payload = build_image_provider_payload(request)
    return await _create_task(db, redis, request, user_id, "image", provider_payload)


def build_image_provider_payload(request: ImageGenerationRequest) -> dict[str, Any]:
    references = [str(url) for url in request.reference_images]
    provider_payload: dict[str, Any] = {
        "model": request.model,
        "prompt": request.prompt,
        "size": request.size,
        "n": request.n,
    }
    if request.model == "gpt-image-2":
        if request.resolution:
            provider_payload["resolution"] = request.resolution.lower()
        provider_payload["response_format"] = "url"
        if references:
            provider_payload["reference_images"] = references
        return provider_payload

    metadata: dict[str, Any] = {}
    if request.resolution:
        metadata["resolution"] = request.resolution
    if request.model in {"doubao-seedream-5-0", "doubao-seedream-5-0-pro"}:
        metadata["watermark"] = False
    if request.google_search:
        metadata["google_search"] = True
    if request.google_image_search:
        metadata["google_image_search"] = True
    if metadata:
        provider_payload["metadata"] = metadata
    if references:
        provider_payload["image_urls"] = references
    return provider_payload


async def create_audio_task(
    db: AsyncSession,
    redis: Any,
    request: AudioGenerationRequest,
    user_id: uuid.UUID,
) -> GenerationTask:
    return await _create_task(
        db,
        redis,
        request,
        user_id,
        "audio",
        build_audio_provider_payload(request),
        provider="volcengine",
        include_client_business_id=False,
    )


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
    reference_videos = [str(url) for url in request.reference_videos]
    reference_audios = [str(url) for url in request.reference_audios]
    provider_payload = {
        "model": request.model,
        "prompt": request.prompt,
        "duration": request.duration,
        "resolution": request.resolution,
        "aspect_ratio": request.aspect_ratio,
    }
    provider_payload["generate_audio"] = request.generate_audio is not False
    if request.return_last_frame:
        provider_payload["return_last_frame"] = True
    if reference_images:
        provider_payload["image_with_roles"] = [
            {"url": url, "role": "reference_image"} for url in reference_images
        ]
    if reference_videos:
        provider_payload["video_with_roles"] = [
            {"url": url, "role": "reference_video"} for url in reference_videos
        ]
    if reference_audios:
        provider_payload["audio_with_roles"] = [
            {"url": url, "role": "reference_audio"} for url in reference_audios
        ]
    return provider_payload


def build_audio_provider_payload(request: AudioGenerationRequest) -> dict[str, Any]:
    references = [{"image_url": str(url)} for url in request.reference_images] or [
        {"audio_url": str(url)} for url in request.reference_audios
    ]
    return {
        "model": request.model,
        "text_prompt": request.prompt,
        "audio_config": {
            "format": request.format,
            "sample_rate": request.sample_rate,
            "speech_rate": request.speech_rate,
            "loudness_rate": request.loudness_rate,
            "pitch_rate": request.pitch_rate,
        },
        **({"references": references} if references else {}),
    }


async def _create_task(
    db: AsyncSession,
    redis: Any,
    request: ImageGenerationRequest | VideoGenerationRequest | AudioGenerationRequest,
    user_id: uuid.UUID,
    task_type: str,
    provider_payload: dict[str, Any],
    provider: str = "toapis",
    include_client_business_id: bool = True,
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
    if include_client_business_id:
        provider_payload["client_business_id"] = str(task_id)
    task = GenerationTask(
        id=task_id,
        user_id=user_id,
        workspace_id=request.workspace_id,
        node_id=request.node_id,
        task_type=task_type,
        provider=provider,
        model=request.model,
        prompt=request.prompt,
        request_snapshot=provider_payload,
    )
    db.add(task)
    resolution = None
    duration = None
    if task_type == "image":
        resolution = request.resolution
    elif task_type == "video":
        duration = request.duration
    await freeze_task_credits(
        db,
        task,
        task_type,
        resolution=resolution,
        duration=duration,
    )
    await db.commit()
    await db.refresh(task)
    try:
        job = await redis.enqueue_job(f"generate_{task_type}", str(task_id))
        if job is None:
            raise RuntimeError("任务重复入队")
    except Exception as exc:
        task.status = "failed"
        task.error_message = "任务入队失败"
        task.finished_at = datetime.now(UTC)
        await refund_task_credits(db, task, "任务入队失败，退还冻结积分")
        await db.commit()
        raise RuntimeError("任务入队失败") from exc
    return task


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
