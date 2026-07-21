from typing import Any

import httpx

from app.core.config import get_settings


class ToApisError(RuntimeError):
    pass


class ToApisProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        settings = get_settings()
        if not settings.toapis_key:
            raise ToApisError("TOAPIS_KEY 未配置")
        self.client = httpx.AsyncClient(
            base_url=settings.toapis_url.rstrip("/"),
            headers={"Authorization": f"Bearer {settings.toapis_key}"},
            timeout=30,
            transport=transport,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    async def submit_image(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/images/generations", json=payload)

    async def get_image_task(self, task_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/images/generations/{task_id}")

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        response = await self.client.request(method, path, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ToApisError(self._error_message(response)) from exc
        data = response.json()
        if not isinstance(data, dict):
            raise ToApisError("ToAPIs 返回格式异常")
        return data

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            error = response.json().get("error")
            if isinstance(error, dict):
                return error.get("message") or f"ToAPIs 请求失败（{response.status_code}）"
            if isinstance(error, str):
                return error
        except ValueError:
            pass
        return f"ToAPIs 请求失败（{response.status_code}）"
