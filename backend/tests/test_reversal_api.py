import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.routes import reversals as reversals_route
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import ContentTemplate, GenerationTask
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


def storyboard_payload(**overrides):
    payload = {
        "workspace_id": str(DEFAULT_WORKSPACE_ID),
        "node_id": "product-storyboard-1",
        "model": "gpt-5.6-sol",
        "media_type": "image",
        "media_url": "https://example.com/product.png",
        "response_mode": "product_storyboard_plan",
        "template_key": "product_storyboard",
        "template_version": 2,
        "template_context": {
            "product_context": "商品名称：测试商品",
            "duration": 30,
            "video_aspect_ratio": "9:16",
            "character_count": 0,
            "product_count": 1,
            "user_requirement": "",
        },
    }
    payload.update(overrides)
    return payload


def product_visual_payload(**overrides):
    payload = {
        "workspace_id": str(DEFAULT_WORKSPACE_ID),
        "node_id": "product-visual-1",
        "model": "gpt-5.6-sol",
        "media_type": "image",
        "media_url": "https://example.com/product-1.png",
        "media_urls": ["https://example.com/product-2.png"],
        "response_mode": "product_visual_plan",
        "template_key": "product_visual",
        "template_version": 2,
        "template_context": {
            "product_context": "商品名称：测试商品",
            "selected_type_ids": ["white-bg", "core-selling"],
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "reference_count": 2,
        },
    }
    payload.update(overrides)
    return payload


def test_product_visual_plan_requires_server_template():
    payload = product_visual_payload()
    assert ReversePromptRequest(**payload).template_key == "product_visual"
    with pytest.raises(ValidationError, match="服务端模板"):
        ReversePromptRequest(**{**payload, "prompt": "生成出图方案"})
    with pytest.raises(ValidationError, match="参考图数量不一致"):
        ReversePromptRequest(**product_visual_payload(
            template_context={**payload["template_context"], "reference_count": 1}
        ))


def test_reverse_prompt_accepts_additional_media_urls():
    payload = ReversePromptRequest(
        workspace_id=DEFAULT_WORKSPACE_ID,
        node_id="outfit-1",
        model="gpt-5.6-sol",
        media_type="image",
        media_url="https://example.com/garment.png",
        media_urls=["https://example.com/model.png"],
        prompt="生成穿搭方案",
        response_mode="outfit_visual_plan",
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
    payload = ReversePromptRequest(**storyboard_payload())
    assert payload.response_mode == "product_storyboard_plan"
    drama_payload = ReversePromptRequest(
        **storyboard_payload(template_key="commerce_drama")
    )
    assert drama_payload.template_key == "commerce_drama"
    with pytest.raises(ValidationError, match="服务端模板"):
        ReversePromptRequest(**storyboard_payload(prompt="生成商品分镜"))
    apparel_payload = ReversePromptRequest(
        workspace_id=DEFAULT_WORKSPACE_ID,
        node_id="apparel-storyboard-1",
        model="gpt-5.6-sol",
        media_type="image",
        media_url="https://example.com/product.png",
        prompt="生成服饰分镜",
        response_mode="apparel_storyboard_plan",
    )
    assert apparel_payload.response_mode == "apparel_storyboard_plan"


def test_product_storyboard_limits_total_reference_images():
    context = {**storyboard_payload()["template_context"], "character_count": 3, "product_count": 3}
    accepted = ReversePromptRequest(**storyboard_payload(
        node_id="product-storyboard-limit",
        media_url="https://example.com/reference-0.png",
        media_urls=[f"https://example.com/reference-{index}.png" for index in range(1, 6)],
        template_context=context,
    ))
    assert len(accepted.media_urls) == 5
    with pytest.raises(ValidationError, match="商品创作最多支持 6 张参考图片"):
        ReversePromptRequest(**storyboard_payload(template_context={
            **context,
            "character_count": 3,
            "product_count": 4,
        }))
    with pytest.raises(ValidationError, match="参考图数量不一致"):
        ReversePromptRequest(**storyboard_payload(template_context={
            **storyboard_payload()["template_context"],
            "character_count": 1,
        }))


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
        async with SessionLocal() as db:
            template = await db.get(ContentTemplate, "product_storyboard")
        response = await client.post("/api/reversals/stream", json=storyboard_payload(
            node_id="long-reverse-test",
            template_version=template.version,
        ))

    events = [json.loads(line) for line in response.text.splitlines()]
    task_id = uuid.UUID(events[0]["task_id"])
    assert events[0]["template_key"] == "product_storyboard"
    assert events[0]["template_version"] == template.version
    assert "".join(event["content"] for event in events if event["type"] == "delta") == "".join(chunks)
    assert "UGC种草统一拍摄风格" in FakeProvider.last_kwargs["prompt"]
    assert FakeProvider.last_kwargs["instructions"].startswith("你是专业的中文电商UGC种草")
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        assert task.result["content"] == "".join(chunks)
        assert task.prompt == FakeProvider.last_kwargs["prompt"]
        assert task.request_snapshot["template_key"] == "product_storyboard"


@pytest.mark.asyncio
async def test_product_visual_stream_uses_server_template(monkeypatch):
    monkeypatch.setattr(reversals_route, "OpenAIResponsesProvider", FakeProvider)
    async with SessionLocal() as db:
        template = await db.get(ContentTemplate, "product_visual")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/reversals/stream",
            json=product_visual_payload(template_version=template.version),
        )

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0] == {
        "type": "meta",
        "task_id": events[0]["task_id"],
        "template_key": "product_visual",
        "template_version": template.version,
        "output_protocol_id": "product-visual-v1",
    }
    assert "white-bg=白底图、core-selling=核心卖点" in FakeProvider.last_kwargs["prompt"]
    assert FakeProvider.last_kwargs["instructions"].startswith(
        "你是专业的中文电商视觉策划师"
    )
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, uuid.UUID(events[0]["task_id"]))
        assert task.prompt == FakeProvider.last_kwargs["prompt"]
        assert task.request_snapshot["template_key"] == "product_visual"
        assert "prompt" not in task.request_snapshot


@pytest.mark.asyncio
async def test_commerce_drama_stream_uses_server_template(monkeypatch):
    monkeypatch.setattr(reversals_route, "OpenAIResponsesProvider", FakeProvider)
    async with SessionLocal() as db:
        template = await db.get(ContentTemplate, "commerce_drama")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/reversals/stream",
            json=storyboard_payload(
                node_id="commerce-drama-test",
                template_key="commerce_drama",
                template_version=template.version,
            ),
        )

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0] == {
        "type": "meta",
        "task_id": events[0]["task_id"],
        "template_key": "commerce_drama",
        "template_version": template.version,
        "output_protocol_id": "commerce-drama-v1",
    }
    assert '"templateId":"commerce-drama"' in FakeProvider.last_kwargs["prompt"]
    assert FakeProvider.last_kwargs["instructions"].startswith("你是专业的中文电商短剧分镜策划师")
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, uuid.UUID(events[0]["task_id"]))
        assert task.request_snapshot["template_key"] == "commerce_drama"
        assert task.prompt == FakeProvider.last_kwargs["prompt"]


@pytest.mark.asyncio
async def test_storyboard_stream_rejects_stale_or_disabled_template():
    async with SessionLocal() as db:
        template = await db.get(ContentTemplate, "product_storyboard")
        version = template.version
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stale = await client.post(
            "/api/reversals/stream",
            json=storyboard_payload(template_version=version + 1),
        )
        assert stale.status_code == 409

        async with SessionLocal() as db:
            template = await db.get(ContentTemplate, "product_storyboard")
            template.enabled = False
            await db.commit()
        disabled = await client.post(
            "/api/reversals/stream",
            json=storyboard_payload(template_version=version),
        )
        assert disabled.status_code == 409
