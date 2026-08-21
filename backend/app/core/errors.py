import re
import traceback
from datetime import UTC, datetime
from typing import Any

import httpx


class ApiError(RuntimeError):
    status_code = 500

    def __init__(self, message: str, data: Any = None):
        super().__init__(message)
        self.message = message
        self.data = data


class NotFoundError(ApiError):
    status_code = 404


class ConflictError(ApiError):
    status_code = 409


class RequestError(ApiError):
    status_code = 422


class InsufficientCreditsError(ApiError):
    status_code = 402


class UpstreamMediaError(ApiError):
    status_code = 502


class ServiceUnavailableError(ApiError):
    status_code = 503


_UPSTREAM_ERROR_NAMES = {
    "OpenAIResponsesError",
    "ToApisError",
    "VolcengineAudioError",
    "ZPayError",
}

DIAGNOSTIC_STAGES = {
    "enqueue",
    "submit",
    "poll",
    "download",
    "storage",
    "billing",
    "unknown",
}
_SECRET_PATTERN = re.compile(
    r"(?i)(authorization|api[-_ ]?key|access[-_ ]?key(?:[-_ ]?(?:id|secret))?|password|token|secret|signature)"
    r"[\"']?\s*[:=]\s*[\"']?(?:bearer\s+)?[^\s,;\"')\]}]+"
)
_URL_PATTERN = re.compile(r"https?://[^\s\]\[()<>\"']+")


def public_error_message(exc: Exception, fallback: str) -> str:
    if isinstance(exc, ApiError):
        return exc.message
    if isinstance(exc, (httpx.HTTPError, OSError, TimeoutError, ConnectionError)):
        return fallback
    if exc.__class__.__name__ in _UPSTREAM_ERROR_NAMES:
        return fallback
    return fallback


def diagnostic_snapshot(exc: Exception, stage: str = "unknown") -> dict[str, Any]:
    stage = stage if stage in DIAGNOSTIC_STAGES else "unknown"
    status_code = _integer_attribute(exc, "status_code")
    request_id = _text_attribute(exc, "request_id")
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        request_id = request_id or next(
            (
                exc.response.headers.get(name)
                for name in ("x-request-id", "request-id", "x-amzn-requestid", "cf-ray")
                if exc.response.headers.get(name)
            ),
            None,
        )
    retryable = bool(getattr(exc, "retryable", False))
    exception_name = exc.__class__.__name__
    is_upstream = exception_name in _UPSTREAM_ERROR_NAMES or isinstance(exc, httpx.HTTPError)

    if status_code:
        category = "upstream_http"
    elif isinstance(exc, (httpx.TimeoutException, TimeoutError)) or "Timeout" in exception_name:
        category = "upstream_timeout"
        retryable = True
    elif isinstance(exc, (httpx.RequestError, ConnectionError)):
        category = "upstream_network"
        retryable = True
    elif stage == "enqueue":
        category = "queue"
        retryable = True
    elif stage == "storage":
        category = "storage"
    elif stage == "billing":
        category = "billing"
    else:
        category = "provider" if is_upstream else "internal"

    message = _safe_provider_message(str(exc)) if is_upstream else "内部异常，详见服务端日志"
    return {
        "stage": stage,
        "category": category,
        "provider_status": status_code,
        "provider_message": message,
        "provider_request_id": request_id,
        "exception_type": exception_name[:120],
        "exception_module": exc.__class__.__module__[:200],
        "exception_message": _safe_diagnostic_text(str(exc)),
        "cause_chain": _cause_chain(exc),
        "traceback": _safe_diagnostic_text("".join(traceback.format_exception(exc))),
        "retryable": retryable,
        "occurred_at": datetime.now(UTC).isoformat(),
    }


def _integer_attribute(exc: Exception, name: str) -> int | None:
    value = getattr(exc, name, None)
    return value if isinstance(value, int) and 100 <= value <= 599 else None


def _text_attribute(exc: Exception, name: str) -> str | None:
    value = getattr(exc, name, None)
    if not isinstance(value, str) or not value.strip():
        return None
    return _safe_provider_message(value, limit=160)


def _safe_provider_message(value: str, limit: int = 500) -> str:
    value = _SECRET_PATTERN.sub(r"\1=[REDACTED]", value)
    value = _URL_PATTERN.sub("[URL]", value)
    value = " ".join(value.split())
    return (value or "上游未返回错误详情")[:limit]


def _safe_diagnostic_text(value: str) -> str:
    return _SECRET_PATTERN.sub(r"\1=[REDACTED]", value)


def _cause_chain(exc: Exception) -> list[dict[str, str]]:
    causes = []
    seen = {id(exc)}
    current = exc
    while True:
        cause = current.__cause__ or (
            current.__context__ if not current.__suppress_context__ else None
        )
        if cause is None or id(cause) in seen:
            return causes
        seen.add(id(cause))
        causes.append(
            {
                "exception_type": cause.__class__.__name__[:120],
                "exception_module": cause.__class__.__module__[:200],
                "exception_message": _safe_diagnostic_text(str(cause)),
            }
        )
        current = cause
