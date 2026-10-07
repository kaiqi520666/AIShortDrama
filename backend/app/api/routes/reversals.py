import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import (
    ConflictError,
    InsufficientCreditsError,
    NotFoundError,
    ServiceUnavailableError,
    RequestError,
    diagnostic_snapshot,
    error_fields,
    public_error_message,
)
from app.core.identity import get_current_user_id
from app.models import ContentTemplate, Workspace
from app.providers.registry import create_text_provider
from app.schemas.reversal import ReversePromptRequest
from app.services.billing import BillingError, InsufficientCredits, freeze_task_credits
from app.services.content_templates import (
    TEMPLATE_BUILDERS,
    TEMPLATE_DEFINITIONS,
    UGC_STORYBOARD_KEY,
)
from app.workers.generation import complete_text_task, fail_task
from app.services.task_lifecycle import create_task, transition_task

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stream")
async def stream_reverse_prompt(
    payload: ReversePromptRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    prompt = payload.prompt
    provider_instruction = None
    template_version = None
    output_protocol_id = None
    if payload.template_key:
        template = await db.get(ContentTemplate, payload.template_key)
        if not template:
            raise ServiceUnavailableError("内容模板服务暂时不可用")
        option_enabled = (
            template.config.get("templates", [{}])[0].get("enabled")
            if template.key == UGC_STORYBOARD_KEY
            else True
        )
        template_label = (
            template.config.get("templates", [{}])[0].get("label")
            if template.key == UGC_STORYBOARD_KEY
            else template.config.get("label")
            or TEMPLATE_DEFINITIONS.get(template.key, {}).get("label")
        ) or "商品模板"
        if not template.enabled or not option_enabled:
            raise ConflictError(f"{template_label}模板已停用，请重新加载", error_key="template_disabled")
        if template.version != payload.template_version:
            raise ConflictError(f"{template_label}模板已更新，请重新加载", error_key="template_updated")
        try:
            prompt = TEMPLATE_BUILDERS[payload.template_key](
                template.config,
                {**payload.template_context.model_dump(), "locale": payload.locale},
            )
        except (KeyError, ValueError) as exc:
            raise RequestError(str(exc)) from exc
        provider_instruction = template.config["provider_instruction"]
        template_version = template.version
        output_protocol_id = template.config.get(
            "output_protocol_id",
            "ugc-seeding",
        )
    workspace = await db.scalar(
        select(Workspace).where(
            Workspace.id == payload.workspace_id,
            Workspace.user_id == user_id,
            Workspace.deleted_at.is_(None),
        )
    )
    if not workspace:
        raise NotFoundError("工作台不存在")
    task = create_task(
        db,
        user_id=user_id,
        workspace_id=payload.workspace_id,
        node_id=payload.node_id,
        task_type=f"{payload.media_type}_reverse",
        provider="aijws",
        model=payload.model,
        prompt=prompt,
        request_snapshot=payload.model_dump(
            mode="json", exclude={"workspace_id", "node_id", "prompt"}
        ),
        started_at=datetime.now(UTC),
    )
    try:
        await freeze_task_credits(db, task, "text")
        await transition_task(db, task.id, "running", source="reverse_stream")
        await db.commit()
        provider = create_text_provider()
    except InsufficientCredits as exc:
        await db.rollback()
        raise InsufficientCreditsError(str(exc)) from exc
    except BillingError as exc:
        await db.rollback()
        raise ServiceUnavailableError(public_error_message(exc, "反推服务暂时不可用")) from exc
    except RuntimeError as exc:
        message = public_error_message(exc, "反推服务暂时不可用")
        logger.exception("Reverse prompt provider initialization failed", extra={"task_id": str(task.id)})
        await fail_task(
            task.id,
            "failed",
            message,
            diagnostic_snapshot(exc, "submit"),
        )
        raise ServiceUnavailableError(message) from exc

    async def events():
        content = ""
        meta = {"type": "meta", "task_id": str(task.id), "generated_locale": payload.locale}
        if payload.template_key:
            meta.update(
                {
                    "template_key": payload.template_key,
                    "template_version": template_version,
                    "output_protocol_id": output_protocol_id,
                }
            )
        yield json.dumps(meta) + "\n"
        try:
            async with provider:
                async for content_chunk in provider.stream_reverse_prompt(
                    model=payload.model,
                    media_type=payload.media_type,
                    media_url=str(payload.media_url),
                    media_urls=[str(url) for url in payload.media_urls],
                    prompt=prompt,
                    response_mode=payload.response_mode,
                    instructions=provider_instruction,
                    locale=payload.locale,
                ):
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
            message = public_error_message(exc, "反推服务暂时不可用")
            logger.exception("Reverse prompt stream failed", extra={"task_id": str(task.id)})
            await fail_task(
                task.id,
                "failed",
                message,
                diagnostic_snapshot(exc, "submit"),
            )
            yield json.dumps({"type": "error", "message": message, **error_fields(exc, status_code=502)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
