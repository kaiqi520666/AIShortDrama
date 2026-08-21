from typing import Any

import httpx

from app.core.config import get_settings


class ToApisError(RuntimeError):
    def __init__(
        self,
        message: str,
        retryable: bool = False,
        status_code: int | None = None,
        request_id: str | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
        self.request_id = request_id
        self.code = code
        self.details = details

    @property
    def public_message(self) -> str | None:
        privacy_error = (self.code or "").lower().endswith("privacyinformation")
        if privacy_error or "may contain real person" in str(self).lower():
            return (
                "参考图片中检测到真人，请在对应图片节点顶部点击人物图标，"
                "注册为 Seedance 人物素材，审核通过后重新生成视频"
            )
        return None


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
        return await self._request(
            "POST",
            "/v1/videos/generations",
            json=payload,
            timeout=httpx.Timeout(180, connect=30),
        )

    async def get_video_task(self, task_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/videos/generations/{task_id}")

    async def create_private_avatar_group(self, name: str) -> dict[str, Any]:
        return self._unwrap_data(await self._request(
            "POST",
            "/v1/videos/doubao-seedance-2-0/private-avatar/groups",
            json={"name": name, "description": "AIShortDrama 虚拟角色"},
        ))

    async def upload_private_avatar(self, group_id: str, source_url: str, name: str) -> dict[str, Any]:
        return self._unwrap_data(await self._request(
            "POST",
            "/v1/videos/doubao-seedance-2-0/private-avatar/assets",
            json={
                "group_id": group_id,
                "asset_type": "image",
                "source_url": source_url,
                "name": name,
            },
        ))

    async def get_private_avatar(self, asset_id: str) -> dict[str, Any]:
        return self._unwrap_data(await self._request(
            "GET",
            f"/v1/videos/doubao-seedance-2-0/private-avatar/assets/{asset_id}",
        ))

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            response = await self.client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ToApisError("ToAPIs 网络请求失败", retryable=True) from exc
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            message, code, details = self._error_details(response)
            raise ToApisError(
                message,
                retryable=response.status_code == 429 or response.status_code >= 500,
                status_code=response.status_code,
                request_id=self._request_id(response),
                code=code,
                details=details,
            ) from exc
        data = response.json()
        if not isinstance(data, dict):
            raise ToApisError("ToAPIs 返回格式异常")
        return data

    @staticmethod
    def _unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("success") is False:
            raise ToApisError(payload.get("message") or "ToAPIs 请求失败")
        data = payload.get("data", payload)
        if not isinstance(data, dict):
            raise ToApisError("ToAPIs 返回格式异常")
        return data

    @staticmethod
    def _error_details(
        response: httpx.Response,
    ) -> tuple[str, str | None, dict[str, Any] | None]:
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                nested = error.get("error") if isinstance(error.get("error"), dict) else error
                message = nested.get("message") or nested.get("detail")
                code = nested.get("code") or error.get("code") or payload.get("code")
                if isinstance(message, str) and message:
                    return message, code if isinstance(code, str) else None, payload
                return f"ToAPIs 请求失败（{response.status_code}）", code if isinstance(code, str) else None, payload
            if isinstance(error, str):
                return error, None, payload
            if isinstance(payload, dict):
                message = payload.get("message") or payload.get("detail")
                code = payload.get("code")
                if isinstance(message, str) and message:
                    text = f"{message}（{code}）" if code and code != message else message
                    return text, code if isinstance(code, str) else None, payload
                if isinstance(code, str) and code:
                    return code, code, payload
        except ValueError:
            pass
        return f"ToAPIs 请求失败（{response.status_code}）", None, None

    @staticmethod
    def _request_id(response: httpx.Response) -> str | None:
        return next(
            (
                response.headers.get(name)
                for name in ("x-request-id", "request-id", "x-amzn-requestid", "cf-ray")
                if response.headers.get(name)
            ),
            None,
        )
