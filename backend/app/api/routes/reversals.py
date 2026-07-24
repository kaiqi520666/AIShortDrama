import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.identity import get_current_user_id
from app.models import GenerationTask, Workspace
from app.providers.dashscope import DashScopeProvider
from app.schemas.response import fail
from app.schemas.reversal import ReversePromptRequest
from app.services.billing import BillingError, freeze_task_credits
from app.workers.generation import complete_text_task, fail_task

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
    try:
        await freeze_task_credits(db, task, "text")
        await db.commit()
        provider = DashScopeProvider()
    except BillingError as exc:
        await db.rollback()
        return JSONResponse(status_code=402, content=fail(str(exc)))
    except RuntimeError as exc:
        await fail_task(task.id, "failed", str(exc))
        return JSONResponse(status_code=503, content=fail(str(exc)))

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
                    content_chunk = content_chunk[: 3000 - len(content)]
                    if not content_chunk:
                        break
                    content += content_chunk
                    yield (
                        json.dumps({"type": "delta", "content": content_chunk}, ensure_ascii=False)
                        + "\n"
                    )
            await complete_text_task(task.id, content)
            yield '{"type":"done"}\n'
        except asyncio.CancelledError:
            await fail_task(task.id, "cancelled", "客户端已中断反推任务")
            raise
        except Exception as exc:
            await fail_task(task.id, "failed", str(exc))
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
