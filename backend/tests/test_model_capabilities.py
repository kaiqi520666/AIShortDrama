import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.identity import DEFAULT_WORKSPACE_ID
from app.core.model_capabilities import MODEL_CAPABILITIES, capabilities_payload
from app.main import app
from app.schemas.generation import (
    AudioGenerationRequest,
    ImageGenerationRequest,
    TextGenerationRequest,
    VideoGenerationRequest,
)


CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "generation-capabilities.v1.json"


@pytest.mark.asyncio
async def test_capabilities_endpoint_returns_public_registry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/generations/capabilities")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["version"] == 1
    assert payload["image"]["default_model"] == "gpt-image-2"
    assert payload["video"]["default_model"] == "seedance-2-mini"
    mini = next(model for model in payload["video"]["models"] if model["id"] == "seedance-2-mini")
    assert mini["duration"] == {"min": 4, "max": 15}
    assert payload["audio"]["models"][0]["formats"] == ["mp3", "wav", "ogg_opus"]
    assert all(not key.startswith("_") for model in payload["image"]["models"] for key in model)


def test_capabilities_registry_matches_cross_platform_contract():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert capabilities_payload() == contract


def test_registry_models_are_accepted_by_request_schemas():
    workspace_id = DEFAULT_WORKSPACE_ID
    for model in capabilities_payload()["text"]["models"]:
        TextGenerationRequest(
            workspace_id=workspace_id, node_id="text", model=model["id"], prompt="test"
        )
    for model in capabilities_payload()["image"]["models"]:
        ImageGenerationRequest(
            workspace_id=workspace_id,
            node_id="image",
            model=model["id"],
            prompt="test",
            size=model["default_aspect_ratio"],
            resolution=model["default_resolution"],
        )
    for model in capabilities_payload()["video"]["models"]:
        VideoGenerationRequest(
            workspace_id=workspace_id,
            node_id="video",
            model=model["id"],
            prompt="test",
            duration=model["default_duration"],
            resolution=model["default_resolution"],
            aspect_ratio=model["default_aspect_ratio"],
        )
    for model in capabilities_payload()["audio"]["models"]:
        AudioGenerationRequest(
            workspace_id=workspace_id, node_id="audio", model=model["id"], prompt="test"
        )


def test_request_limits_follow_registry(monkeypatch):
    image = MODEL_CAPABILITIES["image"]["models"][0]
    monkeypatch.setitem(image, "prompt_max_length", 3)

    with pytest.raises(ValidationError, match="提示词不能超过 3 字符"):
        ImageGenerationRequest(
            workspace_id=DEFAULT_WORKSPACE_ID,
            node_id="image",
            model=image["id"],
            prompt="four",
            size=image["default_aspect_ratio"],
            resolution=image["default_resolution"],
        )
