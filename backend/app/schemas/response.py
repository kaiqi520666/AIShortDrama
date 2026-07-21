from typing import Any


def success(data: Any) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}


def fail(message: str, data: Any = None) -> dict[str, Any]:
    return {"code": 1, "message": message, "data": data}
