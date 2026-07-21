import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import GenerationTask
from app.schemas.generation import ImageGenerationRequest
from app.schemas.response import fail, success
from app.services.generation_tasks import create_image_task, task_payload

router = APIRouter()


@router.post("/images")
async def create_image_generation(
    payload: ImageGenerationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await create_image_task(db, request.app.state.redis, payload)
    except RuntimeError as exc:
        return fail(str(exc))
    return success(task_payload(task))


@router.get("/{task_id}")
async def get_generation_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(GenerationTask, task_id)
    return success(task_payload(task)) if task else fail("任务不存在")
