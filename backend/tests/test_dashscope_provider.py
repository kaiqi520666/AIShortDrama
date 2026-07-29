import json
from types import SimpleNamespace

import httpx
import pytest

from app.providers import dashscope as dashscope_module
from app.providers.dashscope import DashScopeProvider


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


def frame(payload):
    data = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return f"data: {data}\n\n".encode()


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", ["image", "video"])
async def test_stream_reverse_prompt(monkeypatch, media_type):
    requests = []
    chunks = [
        frame({"choices": [{"delta": {"content": "你好"}}]}),
        frame({"choices": [{"delta": {"content": "世界"}}]}),
        frame("[DONE]"),
    ]

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, stream=ChunkStream(chunks))

    monkeypatch.setattr(
        dashscope_module,
        "get_settings",
        lambda: SimpleNamespace(
            dashscope_api_key="secret",
            dashscope_url="https://provider.test/compatible-mode/v1",
        ),
    )
    async with DashScopeProvider(transport=httpx.MockTransport(handler)) as provider:
        content = [
            item
            async for item in provider.stream_reverse_prompt(
                model="qwen3.7-plus",
                media_type=media_type,
                media_url="https://example.com/media",
                prompt="分析素材",
            )
        ]

    payload = json.loads(requests[0].content)
    media = payload["messages"][1]["content"][0]
    assert content == ["你好", "世界"]
    assert requests[0].url.path == "/compatible-mode/v1/chat/completions"
    assert payload["stream"] is True
    assert payload["enable_thinking"] is False
    assert payload["messages"][0]["role"] == "system"
    assert media["type"] == f"{media_type}_url"
    if media_type == "video":
        assert media["fps"] == 2


@pytest.mark.asyncio
async def test_stream_requires_done(monkeypatch):
    async def handler(_request):
        return httpx.Response(
            200,
            stream=ChunkStream([frame({"choices": [{"delta": {"content": "部分"}}]})]),
        )

    monkeypatch.setattr(
        dashscope_module,
        "get_settings",
        lambda: SimpleNamespace(dashscope_api_key="secret", dashscope_url="https://provider.test"),
    )
    async with DashScopeProvider(transport=httpx.MockTransport(handler)) as provider:
        with pytest.raises(RuntimeError, match="未正常结束"):
            _ = [
                item
                async for item in provider.stream_reverse_prompt(
                    model="qwen3.6-flash",
                    media_type="image",
                    media_url="https://example.com/image.png",
                    prompt="分析图片",
                )
            ]


@pytest.mark.asyncio
async def test_product_profile_uses_structured_system_prompt(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            stream=ChunkStream([frame({"choices": [{"delta": {"content": "{}"}}]}), frame("[DONE]")]),
        )

    monkeypatch.setattr(
        dashscope_module,
        "get_settings",
        lambda: SimpleNamespace(dashscope_api_key="secret", dashscope_url="https://provider.test"),
    )
    async with DashScopeProvider(transport=httpx.MockTransport(handler)) as provider:
        _ = [
            item
            async for item in provider.stream_reverse_prompt(
                model="qwen3.7-plus",
                media_type="image",
                media_url="https://example.com/product.png",
                prompt="重点读取包装容量",
                response_mode="product_profile",
            )
        ]

    payload = json.loads(requests[0].content)
    assert "JSON" in payload["messages"][0]["content"]
    prompt = payload["messages"][1]["content"][1]["text"]
    assert '"additionalInfo"' in prompt
    assert "重点读取包装容量" in prompt


@pytest.mark.asyncio
async def test_product_visual_plan_uses_json_system_prompt(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            stream=ChunkStream([frame({"choices": [{"delta": {"content": "[]"}}]}), frame("[DONE]")]),
        )

    monkeypatch.setattr(
        dashscope_module,
        "get_settings",
        lambda: SimpleNamespace(dashscope_api_key="secret", dashscope_url="https://provider.test"),
    )
    async with DashScopeProvider(transport=httpx.MockTransport(handler)) as provider:
        _ = [
            item
            async for item in provider.stream_reverse_prompt(
                model="qwen3.7-plus",
                media_type="image",
                media_url="https://example.com/product.png",
                prompt="生成白底图方案",
                response_mode="product_visual_plan",
            )
        ]

    payload = json.loads(requests[0].content)
    assert "JSON 数组" in payload["messages"][0]["content"]
    assert payload["messages"][1]["content"][1]["text"] == "生成白底图方案"


@pytest.mark.asyncio
async def test_product_visual_plan_accepts_multiple_images(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            stream=ChunkStream([frame({"choices": [{"delta": {"content": "[]"}}]}), frame("[DONE]")]),
        )

    monkeypatch.setattr(
        dashscope_module,
        "get_settings",
        lambda: SimpleNamespace(dashscope_api_key="secret", dashscope_url="https://provider.test"),
    )
    async with DashScopeProvider(transport=httpx.MockTransport(handler)) as provider:
        _ = [
            item
            async for item in provider.stream_reverse_prompt(
                model="qwen3.7-plus",
                media_type="image",
                media_url="https://example.com/garment.png",
                media_urls=["https://example.com/model.png"],
                prompt="生成穿搭方案",
                response_mode="product_visual_plan",
            )
        ]

    content = json.loads(requests[0].content)["messages"][1]["content"]
    assert [item["image_url"]["url"] for item in content[:2]] == [
        "https://example.com/garment.png",
        "https://example.com/model.png",
    ]
    assert content[2]["text"] == "生成穿搭方案"


@pytest.mark.asyncio
async def test_character_profile_uses_character_system_prompt(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            stream=ChunkStream([frame({"choices": [{"delta": {"content": "{}"}}]}), frame("[DONE]")]),
        )

    monkeypatch.setattr(
        dashscope_module,
        "get_settings",
        lambda: SimpleNamespace(dashscope_api_key="secret", dashscope_url="https://provider.test"),
    )
    async with DashScopeProvider(transport=httpx.MockTransport(handler)) as provider:
        _ = [
            item
            async for item in provider.stream_reverse_prompt(
                model="qwen3.7-plus",
                media_type="image",
                media_url="https://example.com/character.png",
                prompt="生成角色档案",
                response_mode="character_profile",
            )
        ]

    system_prompt = json.loads(requests[0].content)["messages"][0]["content"]
    assert "短剧角色设定师" in system_prompt
    assert "JSON 结构" in system_prompt


@pytest.mark.asyncio
async def test_stream_text(monkeypatch):
    requests = []
    chunks = [frame({"choices": [{"delta": {"content": "文案"}}]}), frame("[DONE]")]

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, stream=ChunkStream(chunks))

    monkeypatch.setattr(
        dashscope_module,
        "get_settings",
        lambda: SimpleNamespace(
            dashscope_api_key="secret",
            dashscope_url="https://provider.test/compatible-mode/v1",
        ),
    )
    async with DashScopeProvider(transport=httpx.MockTransport(handler)) as provider:
        content = [
            item
            async for item in provider.stream_text(
                model="qwen3.7-plus", prompt="生成商品文案"
            )
        ]

    payload = json.loads(requests[0].content)
    assert content == ["文案"]
    assert payload["messages"][1] == {"role": "user", "content": "生成商品文案"}
    assert payload["enable_thinking"] is False
