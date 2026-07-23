from typing import Any

import httpx

from app.core.config import get_settings


class ToApisError(RuntimeError):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


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

    async def submit_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/videos/generations", json=payload)

    async def get_video_task(self, task_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/videos/generations/{task_id}")

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            response = await self.client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ToApisError("ToAPIs 网络请求失败", retryable=True) from exc
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ToApisError(
                self._error_message(response),
                retryable=response.status_code == 429 or response.status_code >= 500,
            ) from exc
        data = response.json()
        if not isinstance(data, dict):
            raise ToApisError("ToAPIs 返回格式异常")
        return data

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                return error.get("message") or f"ToAPIs 请求失败（{response.status_code}）"
            if isinstance(error, str):
                return error
        except ValueError:
            pass
        return f"ToAPIs 请求失败（{response.status_code}）"
