from datetime import UTC, datetime

from app.models import GenerationTask
from app.providers.protocols import GenerationProvider
from app.services.task_lifecycle import mark_needs_review, update_task


class SubmissionNeedsReview(RuntimeError):
    pass


async def submit_provider_task(
    task: GenerationTask, provider: GenerationProvider
) -> dict:
    """Persist intent before I/O; uncertain submissions must never be blindly retried."""
    token = task.worker_lease_token
    if task.provider_response:
        return task.provider_response
    if task.provider_task_id:
        return {"id": task.provider_task_id}
    if task.submission_started_at:
        recovered = await provider.lookup(task.client_request_id) if provider.supports_lookup else None
        if recovered:
            recovered = {**recovered, "id": recovered.get("id") or task.client_request_id}
            await persist_provider_result(task, recovered)
            return recovered
        if not provider.supports_idempotent_submit:
            await mark_needs_review(
                task.id, "上游提交结果未知，请人工核对后再处理", worker_token=token,
            )
            raise SubmissionNeedsReview("上游提交结果未知，请人工核对后再处理")
    if not await update_task(
        task.id, submission_started_at=datetime.now(UTC), worker_token=token,
        source="provider_submit",
    ):
        raise SubmissionNeedsReview("任务已暂停或交由其他 worker 处理")
    task.submission_started_at = datetime.now(UTC)
    try:
        response = await provider.submit(
            task.request_snapshot, client_request_id=task.client_request_id
        )
    except Exception as exc:
        if getattr(exc, "request_id", None):
            await update_task(
                task.id, provider_request_id=exc.request_id, worker_token=token,
                source="provider_error",
            )
        raise
    await persist_provider_result(task, response)
    return response


async def persist_provider_result(task: GenerationTask, response: dict) -> None:
    provider_task_id = response.get("id") or task.provider_task_id
    provider_request_id = response.get("provider_request_id") or task.provider_request_id
    try:
        persisted = await update_task(
            task.id, provider_task_id=provider_task_id,
            provider_request_id=provider_request_id,
            provider_response=response, worker_token=task.worker_lease_token,
            source="provider_result",
        )
    except Exception as exc:
        raise SubmissionNeedsReview(
            "上游已接受请求，但本地无法保存结果，请人工核查"
        ) from exc
    if not persisted:
        raise SubmissionNeedsReview("任务已暂停或交由其他 worker 处理")
    task.provider_task_id = provider_task_id
    task.provider_request_id = provider_request_id
    task.provider_response = response
