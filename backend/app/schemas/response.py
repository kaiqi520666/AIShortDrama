from typing import Any


def success(data: Any) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}
