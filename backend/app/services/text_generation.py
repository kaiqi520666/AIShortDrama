import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationTask, Workspace
from app.providers.openai_responses import OpenAIResponsesProvider
from app.schemas.generation import TextGenerationRequest
from app.services.billing import freeze_task_credits
from app.services.generation_tasks import WorkspaceNotFoundError
from app.workers.generation import complete_text_task, fail_task


class TextProvider(Protocol):
    async def __aenter__(self) -> "TextProvider": ...

    async def __aexit__(self, *args: Any) -> None: ...

    def stream_text(self, *, model: str, prompt: str) -> AsyncIterator[str]: ...


@dataclass
class PreparedTextGeneration:
    task: GenerationTask
    provider: TextProvider


class TextGenerationService:
    def __init__(
        self,
        provider_factory: Callable[[], TextProvider] | None = None,
        complete_task: Callable[[uuid.UUID, str], Awaitable[None]] = complete_text_task,
        fail_task_handler: Callable[[uuid.UUID, str, str], Awaitable[None]] = fail_task,
    ):
        self.provider_factory = provider_factory or OpenAIResponsesProvider
        self.complete_task = complete_task
        self.fail_task = fail_task_handler

    async def prepare_text_generation(
        self,
        db: AsyncSession,
        payload: TextGenerationRequest,
        user_id: uuid.UUID,
    ) -> PreparedTextGeneration:
        workspace = await db.scalar(
            select(Workspace).where(
                Workspace.id == payload.workspace_id,
                Workspace.user_id == user_id,
                Workspace.deleted_at.is_(None),
            )
        )
        if not workspace:
            raise WorkspaceNotFoundError("工作台不存在")
        task = GenerationTask(
            user_id=user_id,
            workspace_id=payload.workspace_id,
            node_id=payload.node_id,
            task_type="text",
            provider="aijws",
            model=payload.model,
            status="running",
            prompt=payload.prompt,
            request_snapshot=payload.model_dump(
                mode="json", exclude={"workspace_id", "node_id"}
            ),
            started_at=datetime.now(UTC),
        )
        db.add(task)
        try:
            await freeze_task_credits(db, task, "text")
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        try:
            provider = self.provider_factory()
        except RuntimeError as exc:
            await self.fail_task(task.id, "failed", str(exc))
            raise
        return PreparedTextGeneration(task=task, provider=provider)

    async def stream_text_events(
        self,
        prepared: PreparedTextGeneration,
        payload: TextGenerationRequest,
    ) -> AsyncIterator[str]:
        content = ""
        yield json.dumps({"type": "meta", "task_id": str(prepared.task.id)}) + "\n"
        try:
            async with prepared.provider:
                async for chunk in prepared.provider.stream_text(
                    model=payload.model, prompt=payload.prompt
                ):
                    content += chunk
                    yield json.dumps(
                        {"type": "delta", "content": chunk}, ensure_ascii=False
                    ) + "\n"
            await self.complete_task(prepared.task.id, content)
            yield '{"type":"done"}\n'
        except asyncio.CancelledError:
            await self.fail_task(
                prepared.task.id, "cancelled", "客户端已中断文本任务"
            )
            raise
        except Exception as exc:
            await self.fail_task(prepared.task.id, "failed", str(exc))
            yield json.dumps(
                {"type": "error", "message": str(exc)}, ensure_ascii=False
            ) + "\n"
