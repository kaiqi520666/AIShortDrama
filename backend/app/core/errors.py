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


def public_error_message(exc: Exception, fallback: str) -> str:
    if isinstance(exc, ApiError):
        return exc.message
    if isinstance(exc, (httpx.HTTPError, OSError, TimeoutError, ConnectionError)):
        return fallback
    if exc.__class__.__name__ in _UPSTREAM_ERROR_NAMES:
        return fallback
    return fallback
