from __future__ import annotations

from typing import Any, Final

TASK_STATUSES: Final[frozenset[str]] = frozenset(
    {"queued", "running", "succeeded", "failed", "timeout", "cancelled", "needs_review"}
)
TERMINAL_TASK_STATUSES: Final[frozenset[str]] = frozenset(
    {"succeeded", "failed", "timeout", "cancelled"}
)
CREDIT_STATUSES: Final[frozenset[str]] = frozenset({"none", "frozen", "consumed", "refunded"})

ALLOWED_TASK_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "queued": frozenset({"queued", "running", "failed", "timeout", "cancelled", "needs_review"}),
    "running": frozenset(
        {"running", "queued", "succeeded", "failed", "timeout", "cancelled", "needs_review"}
    ),
    "needs_review": frozenset({"needs_review", "queued", "failed", "cancelled"}),
    "succeeded": frozenset({"succeeded"}),
    "failed": frozenset({"failed"}),
    "timeout": frozenset({"timeout"}),
    "cancelled": frozenset({"cancelled"}),
}


class InvalidTaskTransition(ValueError):
    pass


def transition_task(task: Any, status: str, *, progress: int | None = None) -> bool:
    if status not in TASK_STATUSES:
        raise InvalidTaskTransition(f"未知任务状态: {status}")
    current_status = task.status or "queued"
    if status not in ALLOWED_TASK_TRANSITIONS.get(current_status, frozenset()):
        raise InvalidTaskTransition(f"任务不能从 {current_status} 转为 {status}")
    if progress is not None and not 0 <= progress <= 100:
        raise InvalidTaskTransition("任务进度必须在 0 到 100 之间")
    changed = current_status != status or (progress is not None and task.progress != progress)
    task.status = status
    if progress is not None:
        task.progress = progress
    return changed
