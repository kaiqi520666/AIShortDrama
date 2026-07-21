import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationTask
from app.schemas.generation import ImageGenerationRequest


def task_payload(task: GenerationTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
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
) -> GenerationTask:
    task_id = uuid.uuid4()
    provider_payload = request.model_dump(mode="json", exclude={"node_id"})
    provider_payload["client_business_id"] = str(task_id)
    task = GenerationTask(
        id=task_id,
        node_id=request.node_id,
        task_type="image",
        provider="toapis",
        model=request.model,
        prompt=request.prompt,
        request_snapshot=provider_payload,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    try:
        job = await redis.enqueue_job("generate_image", str(task_id))
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
