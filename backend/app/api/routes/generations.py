import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.core.model_capabilities import capabilities_payload
from app.models import GenerationTask, Workspace
from app.providers.openai_responses import OpenAIResponsesProvider
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
from app.services.billing import BillingError, InsufficientCredits, freeze_task_credits
from app.workers.generation import complete_text_task, fail_task

router = APIRouter()


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
):
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == payload.workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
    )
    if not workspace:
        return JSONResponse(status_code=404, content=fail("工作台不存在"))
    task = GenerationTask(
        user_id=user_id,
        workspace_id=payload.workspace_id,
        node_id=payload.node_id,
        task_type="text",
        provider="aijws",
        model=payload.model,
        status="running",
        prompt=payload.prompt,
        request_snapshot=payload.model_dump(mode="json", exclude={"workspace_id", "node_id"}),
        started_at=datetime.now(UTC),
    )
    db.add(task)
    try:
        await freeze_task_credits(db, task, "text")
        await db.commit()
        provider = OpenAIResponsesProvider()
    except InsufficientCredits as exc:
        await db.rollback()
        return JSONResponse(status_code=402, content=fail(str(exc)))
    except BillingError as exc:
        await db.rollback()
        return JSONResponse(status_code=503, content=fail(str(exc)))
    except RuntimeError as exc:
        await fail_task(task.id, "failed", str(exc))
        return JSONResponse(status_code=503, content=fail(str(exc)))

    async def events():
        content = ""
        yield json.dumps({"type": "meta", "task_id": str(task.id)}) + "\n"
        try:
            async with provider:
                async for chunk in provider.stream_text(model=payload.model, prompt=payload.prompt):
                    content += chunk
                    yield json.dumps({"type": "delta", "content": chunk}, ensure_ascii=False) + "\n"
            await complete_text_task(task.id, content)
            yield '{"type":"done"}\n'
        except asyncio.CancelledError:
            await fail_task(task.id, "cancelled", "客户端已中断文本任务")
            raise
        except Exception as exc:
            await fail_task(task.id, "failed", str(exc))
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        events(),
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
