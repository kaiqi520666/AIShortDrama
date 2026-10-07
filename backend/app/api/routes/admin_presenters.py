from app.models import GenerationTask, ModelPriceRule, User
from app.services.admin import price_snapshot, user_snapshot


def page_data(page: int, page_size: int, total: int, items: list[dict]) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def user_data(user: User) -> dict:
    return {"id": str(user.id), **user_snapshot(user), "created_at": user.created_at.isoformat()}


def rule_data(rule: ModelPriceRule) -> dict:
    return {
        "id": str(rule.id),
        **price_snapshot(rule),
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


def task_summary_data(task: GenerationTask, user: User) -> dict:
    return {
        "id": str(task.id),
        "user": {"id": str(user.id), "username": user.username, "email": user.email},
        "task_type": task.task_type,
        "provider": task.provider,
        "model": task.model,
        "status": task.status,
        "progress": task.progress,
        "provider_task_id": task.provider_task_id,
        "client_request_id": task.client_request_id,
        "provider_request_id": task.provider_request_id,
        "submission_started_at": (
            task.submission_started_at.isoformat() if task.submission_started_at else None
        ),
        "frozen_credits": task.frozen_credits,
        "charged_credits": task.charged_credits,
        "credit_status": task.credit_status,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def task_detail_data(task: GenerationTask, user: User) -> dict:
    return {
        **task_summary_data(task, user),
        "workspace_id": str(task.workspace_id),
        "node_id": task.node_id,
        "diagnostic_snapshot": task.diagnostic_snapshot,
        "request_snapshot": task.request_snapshot,
        "pricing_snapshot": task.pricing_snapshot,
        "result": task.result,
        "retry_count": task.retry_count,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "updated_at": task.updated_at.isoformat(),
    }
