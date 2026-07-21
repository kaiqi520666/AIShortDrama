import json

import httpx
import pytest

from app.providers.toapis import ToApisProvider


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
