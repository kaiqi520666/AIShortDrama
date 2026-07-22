import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal, get_db
from app.core.identity import get_current_user_id
from app.models import GenerationTask, Workspace
from app.providers.dashscope import DashScopeProvider
from app.schemas.response import fail
from app.schemas.reversal import ReversePromptRequest

router = APIRouter()


@router.post("/stream")
async def stream_reverse_prompt(
    payload: ReversePromptRequest,
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
    try:
        provider = DashScopeProvider()
    except RuntimeError as exc:
        return JSONResponse(status_code=503, content=fail(str(exc)))

    task = GenerationTask(
        user_id=user_id,
        workspace_id=payload.workspace_id,
        node_id=payload.node_id,
        task_type=f"{payload.media_type}_reverse",
        provider="dashscope",
        model=payload.model,
        status="running",
        prompt=payload.prompt,
        request_snapshot=payload.model_dump(mode="json", exclude={"workspace_id", "node_id"}),
        started_at=datetime.now(UTC),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    async def update_task(**values):
        async with SessionLocal() as session:
            current = await session.get(GenerationTask, task.id)
            if current:
                for key, value in values.items():
                    setattr(current, key, value)
                await session.commit()

    async def events():
        content = ""
        yield json.dumps({"type": "meta", "task_id": str(task.id)}) + "\n"
        try:
            async with provider:
                async for content_chunk in provider.stream_reverse_prompt(
                    model=payload.model,
                    media_type=payload.media_type,
                    media_url=str(payload.media_url),
                    prompt=payload.prompt,
                ):
                    content += content_chunk
                    yield (
                        json.dumps({"type": "delta", "content": content_chunk}, ensure_ascii=False)
                        + "\n"
                    )
            await update_task(
                status="succeeded",
                progress=100,
                result={"type": "text", "content": content},
                finished_at=datetime.now(UTC),
            )
            yield '{"type":"done"}\n'
        except asyncio.CancelledError:
            await update_task(
                status="cancelled",
                error_message="客户端已中断反推任务",
                finished_at=datetime.now(UTC),
            )
            raise
        except Exception as exc:
            await update_task(
                status="failed",
                error_message=str(exc)[:2000],
                finished_at=datetime.now(UTC),
            )
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
