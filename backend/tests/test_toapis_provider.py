import json

import httpx
import pytest

from app.core.errors import public_error_message
from app.providers.toapis import ToApisError, ToApisProvider


@pytest.mark.asyncio
async def test_submit_and_query_image_task():
    requests = []

    async def handler(request: httpx.Request):
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, json={"id": "task-1", "status": "queued"})
        return httpx.Response(
            200,
            json={
                "id": "task-1",
                "status": "completed",
                "progress": 100,
                "result": {"type": "image", "data": [{"url": "https://example.com/a.png"}]},
            },
        )

    async with ToApisProvider(transport=httpx.MockTransport(handler)) as provider:
        submitted = await provider.submit_image({"model": "gpt-image-2", "prompt": "test"})
        completed = await provider.get_image_task(submitted["id"])

    assert completed["result"]["data"][0]["url"] == "https://example.com/a.png"
    assert requests[0].url.path == "/v1/images/generations"
    assert json.loads(requests[0].content)["model"] == "gpt-image-2"
    assert requests[1].url.path == "/v1/images/generations/task-1"


@pytest.mark.asyncio
async def test_submit_and_query_video_task():
    requests = []

    async def handler(request: httpx.Request):
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, json={"id": "task-2", "status": "queued"})
        return httpx.Response(
            200,
            json={
                "id": "task-2",
                "status": "completed",
                "progress": 100,
                "result": {"type": "video", "data": [{"url": "https://example.com/a.mp4"}]},
            },
        )

    async with ToApisProvider(transport=httpx.MockTransport(handler)) as provider:
        submitted = await provider.submit_video({"model": "seedance-2", "prompt": "test"})
        completed = await provider.get_video_task(submitted["id"])

    assert completed["result"]["data"][0]["url"] == "https://example.com/a.mp4"
    assert requests[0].url.path == "/v1/videos/generations"
    assert requests[0].extensions["timeout"]["read"] == 180
    assert requests[1].url.path == "/v1/videos/generations/task-2"
    assert requests[1].extensions["timeout"]["read"] == 30


@pytest.mark.asyncio
async def test_private_avatar_registration_flow():
    requests = []

    async def handler(request: httpx.Request):
        requests.append(request)
        if request.url.path.endswith("/groups"):
            return httpx.Response(200, json={"success": True, "data": {"group_id": "pg-1"}})
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "asset_id": "pa-1",
                        "asset_url": "asset://pa-1",
                        "status": "processing",
                    },
                },
            )
        return httpx.Response(
            200,
            json={"success": True, "data": {"asset_id": "pa-1", "status": "active"}},
        )

    async with ToApisProvider(transport=httpx.MockTransport(handler)) as provider:
        group = await provider.create_private_avatar_group("角色 A")
        asset = await provider.upload_private_avatar(
            group["group_id"], "https://example.com/character.png", "角色 A"
        )
        state = await provider.get_private_avatar(asset["asset_id"])

    assert group["group_id"] == "pg-1"
    assert asset["asset_url"] == "asset://pa-1"
    assert state["status"] == "active"
    assert requests[0].url.path.endswith("/private-avatar/groups")
    assert json.loads(requests[1].content) == {
        "group_id": "pg-1",
        "asset_type": "image",
        "source_url": "https://example.com/character.png",
        "name": "角色 A",
    }
    assert requests[2].url.path.endswith("/private-avatar/assets/pa-1")


@pytest.mark.asyncio
async def test_http_error_preserves_top_level_provider_message():
    provider = ToApisProvider(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                400,
                headers={"x-request-id": "req-invalid-reference"},
                json={"code": "invalid_parameter", "message": "参考图片不符合要求"},
            )
        )
    )
    try:
        with pytest.raises(ToApisError, match="参考图片不符合要求（invalid_parameter）") as exc_info:
            await provider.submit_video({"model": "seedance-2-mini"})
        assert exc_info.value.public_message is None
        assert exc_info.value.code == "invalid_parameter"
        assert exc_info.value.status_code == 400
        assert exc_info.value.request_id == "req-invalid-reference"
    finally:
        await provider.client.aclose()


@pytest.mark.asyncio
async def test_http_error_maps_real_person_privacy_failure_for_users():
    payload = {
        "code": "fail_to_fetch_task",
        "data": None,
        "message": {
            "error": {
                "code": "InputImage.PrivacyInformation",
                "message": "The request failed because the input image 'content[1]' may contain real person.",
                "param": "",
                "type": "BadRequest",
            }
        }
    }
    provider = ToApisProvider(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(400, json=payload)
        )
    )
    try:
        with pytest.raises(ToApisError) as exc_info:
            await provider.submit_video({"model": "seedance-2-mini"})
        error = exc_info.value
        assert error.code == "InputImage.PrivacyInformation"
        assert error.details == payload
        assert public_error_message(error, "视频生成服务暂时不可用") == (
            "参考图片中检测到真人，请在对应图片节点顶部点击人物图标，"
            "注册为 Seedance 人物素材，审核通过后重新生成视频"
        )
    finally:
        await provider.client.aclose()


@pytest.mark.asyncio
async def test_http_error_explains_oversized_reference_image_for_users():
    payload = {
        "code": "fail_to_fetch_task",
        "data": None,
        "message": json.dumps(
            {
                "error": {
                    "code": "InvalidParameter",
                    "message": (
                        "Error while downloading image, error: expected the width to be at most "
                        "6000px, but received a 6102x4068px image instead"
                    ),
                    "param": "image_url",
                    "type": "BadRequest",
                }
            }
        ),
    }
    provider = ToApisProvider(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(400, json=payload)
        )
    )
    try:
        with pytest.raises(ToApisError) as exc_info:
            await provider.submit_video({"model": "seedance-2-mini"})
        error = exc_info.value
        assert error.details == payload
        assert public_error_message(error, "视频生成服务暂时不可用") == (
            "参考图片尺寸过大：6102×4068px，宽度不能超过 "
            "6000px，请缩小图片后重新生成视频"
        )
    finally:
        await provider.client.aclose()
