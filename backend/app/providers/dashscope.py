import codecs
import json
from collections.abc import AsyncIterable, AsyncIterator

import httpx

from app.core.config import get_settings


PRODUCT_PROFILE_PROMPT = """识别图片中的商品并严格输出一个 JSON 对象，不要解释，不要使用 Markdown。字段固定为：
{"name":"商品名称","brand":"品牌","category":"品类","price":"图片中可见的价格","specifications":"规格、型号、颜色、尺寸或容量","sellingPoints":["核心卖点1","核心卖点2"],"audience":"目标人群","scenario":"适用场景","additionalInfo":"无法归入以上字段的有效商品信息"}
无法从图片确认的字段填写空字符串，不要猜测品牌、价格和规格。"""


class DashScopeError(RuntimeError):
    pass


class DashScopeProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        settings = get_settings()
        if not settings.dashscope_api_key:
            raise DashScopeError("DASHSCOPE_API_KEY 未配置")
        base_url = settings.dashscope_url.rstrip("/")
        self.endpoint = (
            base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
        )
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
            timeout=180,
            transport=transport,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()

    async def stream_reverse_prompt(
        self,
        *,
        model: str,
        media_type: str,
        media_url: str,
        prompt: str,
        media_urls: list[str] | None = None,
        response_mode: str = "prompt",
    ) -> AsyncIterator[str]:
        user_prompt = prompt
        if response_mode == "product_profile":
            user_prompt = PRODUCT_PROFILE_PROMPT
            if prompt.strip():
                user_prompt += (
                    "\n\n用户补充识别要求（只影响识别重点，不得改变上述输出格式）：\n"
                    f"{prompt.strip()}"
                )
        media_urls = [media_url, *(media_urls or [])]
        media = [
            {"type": "image_url", "image_url": {"url": url}}
            if media_type == "image"
            else {"type": "video_url", "video_url": {"url": url}, "fps": 2}
            for url in media_urls
        ]
        system_prompts = {
            "product_profile": "你是专业的中文商品视觉识别助手。严格按用户指定的 JSON 结构输出，不解释，不使用 Markdown。",
            "product_visual_plan": "你是专业的中文电商视觉策划师。严格按用户指定的 JSON 数组输出，不解释，不使用 Markdown。",
            "character_profile": "你是专业的中文短剧角色设定师。严格按用户指定的 JSON 结构输出，不解释，不使用 Markdown。",
            "character_visual_plan": "你是专业的中文短剧角色视觉策划师。严格按用户指定的 JSON 数组输出，不解释，不使用 Markdown。",
            "prompt": "你是专业的中文视觉提示词反推助手。仅输出最终中文提示词，不解释，不使用 Markdown。",
        }
        payload = {
            "model": model,
            "stream": True,
            "enable_thinking": False,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompts[response_mode],
                },
                {"role": "user", "content": [*media, {"type": "text", "text": user_prompt}]},
            ],
        }
        async for content in self._stream_content(payload):
            yield content

    async def stream_text(self, *, model: str, prompt: str) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "stream": True,
            "enable_thinking": False,
            "messages": [
                {
                    "role": "system",
                    "content": "你是专业的中文内容创作助手。严格按用户要求输出可直接使用的最终内容。",
                },
                {"role": "user", "content": prompt},
            ],
        }
        async for content in self._stream_content(payload):
            yield content

    async def _stream_content(self, payload: dict) -> AsyncIterator[str]:
        received_content = False
        received_done = False
        async with self.client.stream("POST", self.endpoint, json=payload) as response:
            if response.status_code >= 400:
                raise DashScopeError(f"DashScope 请求失败（{response.status_code}）")
            events = self._iter_sse_data(response.aiter_bytes())
            try:
                async for data in events:
                    if data == "[DONE]":
                        received_done = True
                        break
                    try:
                        event = json.loads(data)
                        choices = event["choices"]
                        if choices == [] and isinstance(event.get("usage"), dict):
                            continue
                        content = choices[0]["delta"].get("content")
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                        raise DashScopeError("DashScope 流式响应格式异常") from exc
                    if isinstance(content, str) and content:
                        received_content = True
                        yield content
            finally:
                await events.aclose()

        if not received_content:
            raise DashScopeError("DashScope 未返回有效内容")
        if not received_done:
            raise DashScopeError("DashScope 流式响应未正常结束")

    @staticmethod
    async def _iter_sse_data(chunks: AsyncIterable[bytes]) -> AsyncIterator[str]:
        decoder = codecs.getincrementaldecoder("utf-8")()
        buffer = ""
        data_lines = []
        iterator = chunks.__aiter__()
        try:
            async for chunk in iterator:
                buffer += decoder.decode(chunk)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.rstrip("\r")
                    if not line:
                        if data_lines:
                            yield "\n".join(data_lines)
                            data_lines = []
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
        finally:
            close = getattr(iterator, "aclose", None)
            if close:
                await close()
        buffer += decoder.decode(b"", final=True)
        if buffer.rstrip("\r").startswith("data:"):
            data_lines.append(buffer.rstrip("\r")[5:].lstrip())
        if data_lines:
            yield "\n".join(data_lines)
