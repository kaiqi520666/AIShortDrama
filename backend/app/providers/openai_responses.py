import codecs
import json
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.generation_locale import GenerationLocale, output_language_instruction


PRODUCT_PROFILE_PROMPT = """识别图片中的商品并严格输出一个 JSON 对象，不要解释，不要使用 Markdown。字段固定为：
{"name":"商品名称","brand":"品牌","category":"品类","price":"图片中可见的价格","specifications":"规格、型号、颜色、尺码或容量","packagingType":"无包装、带包装、套装或空字符串","productDimensions":"主体商品明确可见的物理尺寸","packageDimensions":"外包装明确可见的物理尺寸","packageRelation":"内件数量、排列及其与外包装的关系","scaleReference":"图片中明确可见的手持、桌面或其他相对尺度参照","sellingPoints":["核心卖点1","核心卖点2"],"audience":"目标人群","scenario":"适用场景","additionalInfo":"无法归入以上字段的有效商品信息"}
无法从图片确认的字段填写空字符串，不要根据画面透视猜测物理尺寸，不要猜测品牌、价格和规格。"""

APPAREL_PROFILE_PROMPT = """识别图片中所有可独立穿戴的服饰与配件，并严格输出一个 JSON 对象，不要解释，不要使用 Markdown。格式固定为：
{"compositionType":"single 或 set","summary":"整体风格、配色和适用场景","items":[{"name":"单品名称","category":"上衣、裤装、裙装、外套、鞋履或配饰等","color":"可见颜色","material":"可确认的面料，不确定则留空","silhouette":"版型、长度或轮廓","details":"领型、袖型、图案、工艺及其他可见特征"}]}
单件服饰使用 single，多件搭配使用 set；每件独立服饰各占一项，一双鞋只算一项，西装外套与西裤分别计项，领带等配饰单独计项。只识别图片中可见内容，不猜测品牌、材质或被遮挡细节。"""


PRODUCT_PROFILE_PROMPT_ID = """Identifikasi produk pada gambar dan keluarkan hanya objek JSON berikut tanpa Markdown:
{"name":"nama produk","brand":"merek","category":"kategori","price":"harga yang terlihat","specifications":"spesifikasi, model, warna, ukuran atau kapasitas","packagingType":"jenis kemasan atau string kosong","productDimensions":"dimensi produk yang tertulis jelas","packageDimensions":"dimensi kemasan yang tertulis jelas","packageRelation":"jumlah, susunan dan hubungan isi dengan kemasan","scaleReference":"acuan skala yang terlihat","sellingPoints":["keunggulan utama"],"audience":"target pengguna","scenario":"situasi penggunaan","additionalInfo":"informasi produk lainnya"}
Gunakan string kosong untuk informasi yang tidak dapat dipastikan. Jangan menebak merek, harga, spesifikasi atau dimensi fisik dari perspektif gambar."""


class OpenAIResponsesError(RuntimeError):
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


class OpenAIResponsesProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        settings = get_settings()
        if not settings.aijws_api_key:
            raise OpenAIResponsesError("AIJWS_API_KEY 未配置")
        base_url = settings.aijws_base_url.rstrip("/")
        self.endpoint = base_url if base_url.endswith("/responses") else f"{base_url}/responses"
        self.reasoning_effort = settings.aijws_reasoning_effort
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {settings.aijws_api_key}"},
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
        instructions: str | None = None,
        locale: GenerationLocale = "zh-CN",
    ) -> AsyncIterator[str]:
        if media_type != "image":
            raise OpenAIResponsesError("GPT-5.6 Sol 当前仅支持图片识别，不支持视频或音频识别")
        user_prompt = prompt
        if response_mode in {"product_profile", "apparel_profile"}:
            user_prompt = PRODUCT_PROFILE_PROMPT if response_mode == "product_profile" else APPAREL_PROFILE_PROMPT
            if response_mode == "product_profile" and locale == "id":
                user_prompt = PRODUCT_PROFILE_PROMPT_ID
            if prompt.strip():
                user_prompt += (
                    ("\n\nPersyaratan tambahan (jangan mengubah struktur JSON):\n" if locale == "id"
                     else "\n\n用户补充识别要求（只影响识别重点，不得改变上述输出格式）：\n")
                    + prompt.strip()
                )
        image_urls = [media_url, *(media_urls or [])]
        content: list[dict[str, Any]] = [
            {"type": "input_image", "image_url": url, "detail": "original"}
            for url in image_urls
        ]
        content.append({"type": "input_text", "text": user_prompt})
        system_prompts = {
            "product_profile": "你是专业的中文商品视觉识别助手。严格按用户指定的 JSON 结构输出，不解释，不使用 Markdown。",
            "apparel_profile": "你是专业的中文服饰视觉识别助手。严格按用户指定的 JSON 结构输出，不解释，不使用 Markdown。",
            "outfit_visual_plan": "你是专业的中文电商视觉策划师。严格按用户指定的 JSON 数组输出，不解释，不使用 Markdown。",
            "product_storyboard_plan": "你是专业的中文电商UGC种草分镜策划师。完整执行用户提示词，并严格按其中指定的 JSON 结构输出，不解释，不使用 Markdown。",
            "prompt": "你是专业的中文视觉提示词反推助手。仅输出最终中文提示词，不解释，不使用 Markdown。",
        }
        if locale == "id":
            system_prompts = {
                "product_profile": "Anda ahli identifikasi produk. Keluarkan hanya JSON sesuai skema.",
                "apparel_profile": "Anda ahli identifikasi pakaian. Keluarkan hanya JSON sesuai skema.",
                "outfit_visual_plan": "Anda perencana visual e-commerce. Ikuti struktur JSON yang diminta.",
                "product_storyboard_plan": "Anda sutradara storyboard e-commerce. Ikuti struktur JSON yang diminta.",
                "prompt": "Anda ahli analisis visual. Keluarkan hanya prompt akhir dalam bahasa Indonesia, tanpa penjelasan atau Markdown.",
            }
        system_instruction = instructions or system_prompts[response_mode]
        if locale == "id":
            system_instruction = system_instruction.replace("中文", "印度尼西亚语")
        payload = {
            "model": model,
            "stream": True,
            "reasoning": {"effort": self.reasoning_effort},
            "instructions": system_instruction + "\n" + output_language_instruction(locale),
            "input": [{"role": "user", "content": content}],
        }
        async for text in self._stream_content(payload):
            yield text

    async def stream_text(self, *, model: str, prompt: str, locale: GenerationLocale = "zh-CN") -> AsyncIterator[str]:
        payload = {
            "model": model,
            "stream": True,
            "reasoning": {"effort": self.reasoning_effort},
            "instructions": (
                "Anda penulis profesional. Ikuti permintaan pengguna dan keluarkan konten akhir yang siap digunakan."
                if locale == "id" else "你是专业的中文内容创作助手。严格按用户要求输出可直接使用的最终内容。"
            ) + "\n" + output_language_instruction(locale),
            "input": prompt,
        }
        async for text in self._stream_content(payload):
            yield text

    async def _stream_content(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        received_content = False
        received_done = False
        async with self.client.stream("POST", self.endpoint, json=payload) as response:
            request_id = response.headers.get("x-request-id") or response.headers.get(
                "request-id"
            )
            if response.status_code >= 400:
                raise OpenAIResponsesError(
                    await self._response_error_message(response),
                    retryable=response.status_code == 429 or response.status_code >= 500,
                    status_code=response.status_code,
                    request_id=request_id,
                )
            events = self._iter_sse_data(response.aiter_bytes())
            try:
                async for data in events:
                    if data == "[DONE]":
                        received_done = True
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError as exc:
                        raise OpenAIResponsesError("Responses 流式响应格式异常") from exc
                    event_type = event.get("type")
                    if event_type == "response.output_text.delta":
                        content = event.get("delta")
                        if isinstance(content, str) and content:
                            received_content = True
                            yield content
                    elif event_type == "response.output_text.done" and not received_content:
                        content = event.get("text")
                        if isinstance(content, str) and content:
                            received_content = True
                            yield content
                    elif event_type in {"response.failed", "response.incomplete", "error"}:
                        error = event.get("error") or {}
                        message = error.get("message") if isinstance(error, dict) else str(error)
                        raise OpenAIResponsesError(
                            message or "Responses 生成失败",
                            request_id=request_id,
                        )
                    elif event_type == "response.completed":
                        response_data = event.get("response") or {}
                        if response_data.get("error"):
                            error = response_data["error"]
                            message = error.get("message") if isinstance(error, dict) else str(error)
                            raise OpenAIResponsesError(
                                message or "Responses 生成失败",
                                request_id=request_id,
                            )
                        received_done = True
            finally:
                await events.aclose()

        if not received_content:
            raise OpenAIResponsesError("Responses 未返回有效内容")
        if not received_done:
            raise OpenAIResponsesError("Responses 流式响应未正常结束")

    @staticmethod
    async def _response_error_message(response: httpx.Response) -> str:
        try:
            payload = json.loads(await response.aread())
        except (ValueError, UnicodeDecodeError):
            return f"Responses 请求失败（{response.status_code}）"
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = error.get("message") or error.get("detail")
            if isinstance(message, str) and message:
                return message
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("detail")
            if isinstance(message, str) and message:
                return message
        return f"Responses 请求失败（{response.status_code}）"

    @staticmethod
    async def _iter_sse_data(chunks: AsyncIterable[bytes]) -> AsyncIterator[str]:
        decoder = codecs.getincrementaldecoder("utf-8")()
        buffer = ""
        data_lines: list[str] = []
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
