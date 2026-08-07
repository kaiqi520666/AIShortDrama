import uuid
from typing import Any

import httpx

from app.core.config import get_settings


class VolcengineAudioError(RuntimeError):
    def __init__(
        self,
        message: str,
        retryable: bool = False,
        status_code: int | None = None,
        request_id: str | None = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
        self.request_id = request_id


class VolcengineAudioProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        settings = get_settings()
        if not settings.volcengine_speech_api_key:
            raise VolcengineAudioError("VOLCENGINE_SPEECH_API_KEY 未配置")
        self.url = settings.volcengine_speech_url
        self.client = httpx.AsyncClient(
            headers={"X-Api-Key": settings.volcengine_speech_api_key},
            timeout=httpx.Timeout(300, connect=30),
            transport=transport,
        )

    async def synthesize(self, payload: dict[str, Any]) -> dict[str, Any]:
        client_request_id = str(uuid.uuid4())
        try:
            response = await self.client.post(
                self.url,
                json=payload,
                headers={"X-Api-Request-Id": client_request_id},
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise VolcengineAudioError(
                "火山音频接口网络请求失败",
                retryable=True,
                request_id=client_request_id,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise VolcengineAudioError(
                f"火山音频接口请求失败（{response.status_code}）",
                retryable=response.status_code == 429 or response.status_code >= 500,
                status_code=response.status_code,
                request_id=self._request_id(response) or client_request_id,
            ) from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise VolcengineAudioError("火山音频接口返回格式异常") from exc
        if not isinstance(data, dict) or data.get("code") != 0:
            message = data.get("message") if isinstance(data, dict) else None
            raise VolcengineAudioError(
                message or "火山音频生成失败",
                request_id=self._request_id(response) or client_request_id,
            )
        return data

    @staticmethod
    def _request_id(response: httpx.Response) -> str | None:
        return response.headers.get("x-request-id") or response.headers.get(
            "x-api-request-id"
        )
