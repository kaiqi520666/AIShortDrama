import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.routes import reversals as reversals_route
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import GenerationTask
from app.schemas.reversal import ReversePromptRequest


class FakeProvider:
    last_kwargs = None
    chunks = ("第一段", "第二段")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def stream_reverse_prompt(self, **_kwargs):
        self.__class__.last_kwargs = _kwargs
        for chunk in self.chunks:
            yield chunk


def test_product_visual_plan_requires_prompt():
    payload = {
        "workspace_id": str(DEFAULT_WORKSPACE_ID),
        "node_id": "product-visual-1",
        "model": "gpt-5.6-sol",
        "media_type": "image",
        "media_url": "https://example.com/product.png",
        "response_mode": "product_visual_plan",
    }
    with pytest.raises(ValidationError, match="提示词不能为空"):
        ReversePromptRequest(**payload)
    assert ReversePromptRequest(**{**payload, "prompt": "生成出图方案"}).response_mode == "product_visual_plan"


def test_reverse_prompt_accepts_additional_media_urls():
    payload = ReversePromptRequest(
        workspace_id=DEFAULT_WORKSPACE_ID,
        node_id="outfit-1",
        model="gpt-5.6-sol",
        media_type="image",
        media_url="https://example.com/garment.png",
        media_urls=["https://example.com/model.png"],
        prompt="生成穿搭方案",
        response_mode="product_visual_plan",
    )
    assert [str(url) for url in payload.media_urls] == ["https://example.com/model.png"]


def test_reverse_prompt_rejects_video_media():
    with pytest.raises(ValidationError):
        ReversePromptRequest(
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="video-reverse-1",
            model="gpt-5.6-sol",
            media_type="video",
            media_url="https://example.com/video.mp4",
            prompt="分析视频",
        )


def test_product_profile_limits_reference_images():
    payload = {
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "node_id": "product-1",
        "model": "gpt-5.6-sol",
        "media_type": "image",
        "media_url": "https://example.com/product-0.png",
        "prompt": "",
        "response_mode": "product_profile",
    }
    accepted = ReversePromptRequest(**{
        **payload,
        "media_urls": [f"https://example.com/product-{index}.png" for index in range(1, 6)],
    })
    assert len(accepted.media_urls) == 5
    with pytest.raises(ValidationError, match="商品创作最多支持 6 张参考图片"):
        ReversePromptRequest(**{
            **payload,
            "media_urls": [f"https://example.com/product-{index}.png" for index in range(1, 7)],
        })


def test_reverse_prompt_accepts_character_response_modes():
    payload = {
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "node_id": "character-1",
        "model": "gpt-5.6-sol",
        "media_type": "image",
        "media_url": "https://example.com/character.png",
        "prompt": "生成角色档案",
    }
    assert ReversePromptRequest(**payload, response_mode="character_profile").response_mode == "character_profile"
    assert ReversePromptRequest(**payload, response_mode="character_visual_plan").response_mode == "character_visual_plan"


def test_reverse_prompt_accepts_apparel_profile_without_prompt():
    payload = ReversePromptRequest(
        workspace_id=DEFAULT_WORKSPACE_ID,
        node_id="apparel-1",
        model="gpt-5.6-sol",
        media_type="image",
        media_url="https://example.com/apparel.png",
        response_mode="apparel_profile",
    )
    assert payload.response_mode == "apparel_profile"


def test_reverse_prompt_accepts_product_storyboard_mode():
    payload = ReversePromptRequest(
        workspace_id=DEFAULT_WORKSPACE_ID,
        node_id="product-storyboard-1",
        model="gpt-5.6-sol",
        media_type="image",
        media_url="https://example.com/product.png",
        prompt="生成商品分镜",
        response_mode="product_storyboard_plan",
    )
    assert payload.response_mode == "product_storyboard_plan"
    apparel_payload = ReversePromptRequest(**{**payload.model_dump(), "node_id": "apparel-storyboard-1", "response_mode": "apparel_storyboard_plan"})
    assert apparel_payload.response_mode == "apparel_storyboard_plan"


def test_product_storyboard_limits_total_reference_images():
    payload = {
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "node_id": "product-storyboard-limit",
        "model": "gpt-5.6-sol",
        "media_type": "image",
        "media_url": "https://example.com/reference-0.png",
        "prompt": "生成商品分镜",
        "response_mode": "product_storyboard_plan",
    }
    accepted = ReversePromptRequest(**{
        **payload,
        "media_urls": [f"https://example.com/reference-{index}.png" for index in range(1, 6)],
    })
    assert len(accepted.media_urls) == 5
    with pytest.raises(ValidationError, match="商品创作最多支持 6 张参考图片"):
        ReversePromptRequest(**{
            **payload,
            "media_urls": [f"https://example.com/reference-{index}.png" for index in range(1, 7)],
        })


@pytest.mark.asyncio
async def test_stream_reverse_prompt(monkeypatch):
    monkeypatch.setattr(reversals_route, "OpenAIResponsesProvider", FakeProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/reversals/stream",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "text-reverse-test",
                "model": "gpt-5.6-sol",
                "media_type": "image",
                "media_url": "https://example.com/image.png",
                "prompt": "",
                "response_mode": "product_profile",
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["type"] == "meta"
    task_id = uuid.UUID(events[0]["task_id"])
    assert events[1:] == [
        {"type": "delta", "content": "第一段"},
        {"type": "delta", "content": "第二段"},
        {"type": "done"},
    ]
    assert FakeProvider.last_kwargs["response_mode"] == "product_profile"
    assert FakeProvider.last_kwargs["prompt"] == ""
    assert FakeProvider.last_kwargs["media_urls"] == []
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.status == "succeeded"
        assert task.result["content"] == "第一段第二段"


@pytest.mark.asyncio
async def test_stream_reverse_prompt_keeps_content_over_3000_characters(monkeypatch):
    chunks = ("甲" * 2000, "乙" * 2000)
    monkeypatch.setattr(FakeProvider, "chunks", chunks)
    monkeypatch.setattr(reversals_route, "OpenAIResponsesProvider", FakeProvider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/reversals/stream",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "long-reverse-test",
                "model": "gpt-5.6-sol",
                "media_type": "image",
                "media_url": "https://example.com/image.png",
                "prompt": "生成完整分镜",
                "response_mode": "product_storyboard_plan",
            },
        )

    events = [json.loads(line) for line in response.text.splitlines()]
    task_id = uuid.UUID(events[0]["task_id"])
    assert "".join(event["content"] for event in events if event["type"] == "delta") == "".join(chunks)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.result["content"] == "".join(chunks)
