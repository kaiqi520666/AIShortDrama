import re
from typing import Any

import httpx


class ApiError(RuntimeError):
    status_code = 500

    def __init__(
        self, message: str, data: Any = None, *,
        error_key: str | None = None, error_params: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.data = data
        self.error_key = error_key
        self.error_params = error_params or {}


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


class LocalizedValueError(ValueError):
    def __init__(
        self, message: str, *,
        error_key: str = "invalid_request", error_params: dict | None = None,
    ):
        super().__init__(message)
        self.error_key = error_key
        self.error_params = error_params or {}


def error_fields(exc: Exception | None = None, *, status_code: int = 500) -> dict[str, Any]:
    current = exc
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, "error_key", None):
            return {"error_key": current.error_key, "error_params": getattr(current, "error_params", {})}
        current = current.__cause__
    key = {
        400: "invalid_request", 401: "unauthorized", 402: "insufficient_credits",
        403: "forbidden", 404: "not_found", 405: "method_not_allowed",
        409: "conflict", 413: "file_too_large", 422: "invalid_request",
        429: "rate_limited", 502: "upstream_unavailable", 503: "service_unavailable",
        504: "task_timeout",
    }.get(status_code, "service_unavailable" if status_code >= 500 else "request_failed")
    return {"error_key": key, "error_params": {}}


def task_error_fields(status: str) -> dict[str, Any]:
    key = {"failed": "generation_failed", "cancelled": "task_cancelled", "timeout": "task_timeout"}.get(status)
    return {"error_key": key, "error_params": {}} if key else {}


_UPSTREAM_ERROR_NAMES = {
    "OpenAIResponsesError",
    "ToApisError",
    "VolcengineAudioError",
    "ZPayError",
}

_SECRET_PATTERN = re.compile(
    r"(?i)(authorization|api[-_ ]?key|access[-_ ]?key(?:[-_ ]?(?:id|secret))?|password|token|secret|signature)"
    r"[\"']?\s*[:=]\s*[\"']?(?:bearer\s+)?[^\s,;\"')\]}]+"
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)^(authorization|api[-_ ]?key|access[-_ ]?key(?:[-_ ]?(?:id|secret))?|password|token|secret|signature)$"
)


def public_error_message(exc: Exception, fallback: str) -> str:
    if isinstance(exc, ApiError):
        return exc.message
    public_message = getattr(exc, "public_message", None)
    if isinstance(public_message, str) and public_message.strip():
        return public_message
    if isinstance(exc, (httpx.HTTPError, OSError, TimeoutError, ConnectionError)):
        return fallback
    if exc.__class__.__name__ in _UPSTREAM_ERROR_NAMES:
        return fallback
    return fallback


def diagnostic_snapshot(exc: Exception, _stage: str = "unknown") -> Any:
    if exc.__class__.__name__ != "ToApisError":
        return None
    details = getattr(exc, "details", None)
    return _safe_diagnostic_value(details) if details is not None else None


def _safe_diagnostic_text(value: str) -> str:
    return _SECRET_PATTERN.sub(r"\1=[REDACTED]", value)


def _safe_diagnostic_value(value: Any) -> Any:
    if isinstance(value, str):
        return _safe_diagnostic_text(value)
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if _SECRET_KEY_PATTERN.fullmatch(str(key))
            else _safe_diagnostic_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_diagnostic_value(item) for item in value]
    return value
