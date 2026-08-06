import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.core.model_capabilities import capabilities_payload
from app.models import GenerationTask
from app.schemas.generation import (
    AudioGenerationRequest,
    ImageGenerationRequest,
    TextGenerationRequest,
    VideoGenerationRequest,
)
from app.schemas.response import fail, success
from app.services.generation_tasks import (
    GenerationQueueError,
    WorkspaceNotFoundError,
    create_audio_task,
    create_image_task,
    create_video_task,
    task_payload,
)
from app.services.billing import BillingError, InsufficientCredits
from app.services.text_generation import TextGenerationService

router = APIRouter()


def get_text_generation_service() -> TextGenerationService:
    return TextGenerationService()


@router.get("/capabilities")
async def get_generation_capabilities(
    _user_id: uuid.UUID = Depends(get_current_user_id),
):
    return success(capabilities_payload())


async def _create_queued_generation(create_task, db, redis, payload, user_id):
    try:
        task = await create_task(db, redis, payload, user_id)
    except WorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content=fail(str(exc)))
    except InsufficientCredits as exc:
        return JSONResponse(status_code=402, content=fail(str(exc)))
    except (BillingError, GenerationQueueError) as exc:
        return JSONResponse(status_code=503, content=fail(str(exc)))
    return success(task_payload(task))


@router.post("/texts")
async def create_text_generation(
    payload: TextGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: TextGenerationService = Depends(get_text_generation_service),
):
    try:
        prepared = await service.prepare_text_generation(db, payload, user_id)
    except WorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content=fail(str(exc)))
    except InsufficientCredits as exc:
        return JSONResponse(status_code=402, content=fail(str(exc)))
    except (BillingError, RuntimeError) as exc:
        return JSONResponse(status_code=503, content=fail(str(exc)))

    return StreamingResponse(
        service.stream_text_events(prepared, payload),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/images")
async def create_image_generation(
    payload: ImageGenerationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await _create_queued_generation(
        create_image_task, db, request.app.state.redis, payload, user_id
    )


@router.post("/videos")
async def create_video_generation(
    payload: VideoGenerationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await _create_queued_generation(
        create_video_task, db, request.app.state.redis, payload, user_id
    )


@router.post("/audios")
async def create_audio_generation(
    payload: AudioGenerationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await _create_queued_generation(
        create_audio_task, db, request.app.state.redis, payload, user_id
    )


@router.get("/{task_id}")
async def get_generation_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    task = await db.get(GenerationTask, task_id)
    if not task or task.user_id != user_id:
        return JSONResponse(status_code=404, content=fail("任务不存在"))
    return success(task_payload(task))
