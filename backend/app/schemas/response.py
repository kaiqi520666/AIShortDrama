from typing import Any


def success(data: Any) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}


def fail(
    message: str, data: Any = None, *,
    error_key: str = "request_failed", error_params: dict | None = None,
) -> dict[str, Any]:
    return {
        "code": 1, "message": message, "data": data,
        "error_key": error_key, "error_params": error_params or {},
    }
