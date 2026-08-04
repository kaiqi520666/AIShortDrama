import json
from types import SimpleNamespace

import httpx
import pytest

from app.providers import openai_responses as provider_module
from app.providers.openai_responses import OpenAIResponsesError, OpenAIResponsesProvider


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


def frame(payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


def settings():
    return SimpleNamespace(
        aijws_api_key="secret",
        aijws_base_url="https://provider.test/v1",
        aijws_reasoning_effort="high",
    )


@pytest.mark.asyncio
async def test_stream_reverse_prompt_uses_responses_image_format(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        chunks = [
            frame({"type": "response.output_text.delta", "delta": "你好"}),
            frame({"type": "response.output_text.delta", "delta": "世界"}),
            frame({"type": "response.completed", "response": {"error": None}}),
        ]
        return httpx.Response(200, stream=ChunkStream(chunks))

    monkeypatch.setattr(provider_module, "get_settings", settings)
    async with OpenAIResponsesProvider(transport=httpx.MockTransport(handler)) as provider:
        content = [
            item
            async for item in provider.stream_reverse_prompt(
                model="gpt-5.6-sol",
                media_type="image",
                media_url="https://example.com/product.png",
                media_urls=["https://example.com/character.png"],
                prompt="生成商品分镜",
                response_mode="product_storyboard_plan",
            )
        ]

    payload = json.loads(requests[0].content)
    message = payload["input"][0]
    assert content == ["你好", "世界"]
    assert requests[0].url.path == "/v1/responses"
    assert payload["stream"] is True
    assert payload["reasoning"] == {"effort": "high"}
    assert "电商短视频分镜策划师" in payload["instructions"]
    assert [item["type"] for item in message["content"]] == [
        "input_image",
        "input_image",
        "input_text",
    ]
    assert message["content"][0]["detail"] == "original"
    assert message["content"][2]["text"] == "生成商品分镜"


@pytest.mark.asyncio
async def test_stream_reverse_prompt_rejects_video(monkeypatch):
    monkeypatch.setattr(provider_module, "get_settings", settings)
    async with OpenAIResponsesProvider(transport=httpx.MockTransport(lambda _: None)) as provider:
        with pytest.raises(OpenAIResponsesError, match="不支持视频或音频识别"):
            _ = [
                item
                async for item in provider.stream_reverse_prompt(
                    model="gpt-5.6-sol",
                    media_type="video",
                    media_url="https://example.com/video.mp4",
                    prompt="分析视频",
                )
            ]


@pytest.mark.asyncio
async def test_stream_requires_completed_event(monkeypatch):
    async def handler(_request):
        return httpx.Response(
            200,
            stream=ChunkStream([frame({"type": "response.output_text.delta", "delta": "部分"})]),
        )

    monkeypatch.setattr(provider_module, "get_settings", settings)
    async with OpenAIResponsesProvider(transport=httpx.MockTransport(handler)) as provider:
        with pytest.raises(OpenAIResponsesError, match="未正常结束"):
            _ = [
                item
                async for item in provider.stream_text(
                    model="gpt-5.6-sol", prompt="生成商品文案"
                )
            ]


@pytest.mark.asyncio
async def test_product_profile_uses_structured_instructions(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            stream=ChunkStream([
                frame({"type": "response.output_text.delta", "delta": "{}"}),
                frame({"type": "response.completed", "response": {}}),
            ]),
        )

    monkeypatch.setattr(provider_module, "get_settings", settings)
    async with OpenAIResponsesProvider(transport=httpx.MockTransport(handler)) as provider:
        _ = [
            item
            async for item in provider.stream_reverse_prompt(
                model="gpt-5.6-sol",
                media_type="image",
                media_url="https://example.com/product.png",
                prompt="重点读取包装容量",
                response_mode="product_profile",
            )
        ]

    payload = json.loads(requests[0].content)
    assert "商品视觉识别助手" in payload["instructions"]
    text = payload["input"][0]["content"][1]["text"]
    assert '"additionalInfo"' in text
    assert '"productDimensions"' in text
    assert "重点读取包装容量" in text


@pytest.mark.asyncio
async def test_stream_text(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            stream=ChunkStream([
                frame({"type": "response.output_text.delta", "delta": "文案"}),
                frame({"type": "response.completed", "response": {}}),
            ]),
        )

    monkeypatch.setattr(provider_module, "get_settings", settings)
    async with OpenAIResponsesProvider(transport=httpx.MockTransport(handler)) as provider:
        content = [
            item
            async for item in provider.stream_text(
                model="gpt-5.6-sol", prompt="生成商品文案"
            )
        ]

    payload = json.loads(requests[0].content)
    assert content == ["文案"]
    assert payload["input"] == "生成商品文案"
    assert payload["reasoning"] == {"effort": "high"}
