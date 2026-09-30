from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any


request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(value: str | None):
    return request_id_context.set(value)


def reset_request_id(token) -> None:
    request_id_context.reset(token)


def current_request_id() -> str | None:
    return request_id_context.get()


@contextmanager
def log_context(**values: Any):
    extra = {key: value for key, value in values.items() if value is not None}
    if current_request_id():
        extra.setdefault("request_id", current_request_id())
    yield extra


def task_log_extra(task_id: Any, **values: Any) -> dict[str, Any]:
    return {
        "request_id": current_request_id(),
        "task_id": str(task_id) if task_id else None,
        **{key: value for key, value in values.items() if value is not None},
    }
