import httpx
import pytest

from app.providers.registry import (
    ProviderConfigurationError,
    ProviderRegistry,
    adapt_generation_provider,
)
from app.providers.toapis import ToApisError, ToApisProvider
from app.providers.volcengine_audio import VolcengineAudioError, VolcengineAudioProvider


class FakeMediaProvider:
    def __init__(self):
        self.closed = False

    async def submit_image(self, payload):
        return {"id": "image-1", "payload": payload}

    async def get_image_task(self, task_id):
        return {"id": task_id, "status": "completed"}

    async def aclose(self):
        self.closed = True


class FakeAudioProvider:
    async def synthesize(self, _payload):
        return {"audio": "ZmFrZQ==", "duration": 1, "original_duration": 1}


@pytest.mark.asyncio
async def test_registry_selects_provider_by_name_and_media_without_closing_caller_instance():
    provider = FakeMediaProvider()
    registry = ProviderRegistry()
    registry.register("test", {"image"}, lambda: provider)
    adapted = registry.create_generation("test", "image")
    assert await adapted.submit({"prompt": "x"}) == {
        "id": "image-1", "payload": {"prompt": "x"}
    }
    assert await adapted.get_task("task-1") == {"id": "task-1", "status": "completed"}
    assert adapted.supports_lookup is False
    assert adapted.supports_idempotent_submit is False
    assert provider.closed is False
    await adapted.aclose()
    assert provider.closed is True
    with pytest.raises(ProviderConfigurationError):
        registry.create_generation("test", "video")


@pytest.mark.asyncio
async def test_audio_adapter_preserves_synchronous_result_and_rejects_lookup():
    adapted = adapt_generation_provider(FakeAudioProvider(), "audio")
    assert await adapted.submit({}, client_request_id="stable-1") == {
        "audio": "ZmFrZQ==", "duration": 1, "original_duration": 1
    }
    assert adapted.supports_lookup is False
    with pytest.raises(ProviderConfigurationError):
        await adapted.get_task("audio-1")
    with pytest.raises(ProviderConfigurationError):
        await adapted.lookup("client-1")


@pytest.mark.asyncio
async def test_new_provider_submission_protocol_receives_stable_client_request_id():
    class NewProvider:
        async def submit(self, payload, *, client_request_id=None):
            return {"payload": payload, "request_id": client_request_id}

    adapted = adapt_generation_provider(NewProvider(), "image")
    assert await adapted.submit({"prompt": "x"}, client_request_id="stable-1") == {
        "payload": {"prompt": "x"}, "request_id": "stable-1"
    }


@pytest.mark.asyncio
async def test_volcengine_uses_stable_request_id_and_records_response_header(monkeypatch):
    monkeypatch.setenv("VOLCENGINE_SPEECH_API_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    calls = []

    def handler(request):
        calls.append(request.headers["X-Api-Request-Id"])
        return httpx.Response(
            200,
            headers={"x-api-request-id": "response-request-1"},
            json={"code": 0, "audio": "ZmFrZQ==", "original_duration": 1},
        )

    provider = VolcengineAudioProvider(transport=httpx.MockTransport(handler))
    adapted = adapt_generation_provider(provider, "audio")
    try:
        result = await adapted.submit({}, client_request_id="stable-request-1")
        assert calls == ["stable-request-1"]
        assert result["provider_request_id"] == "response-request-1"
    finally:
        await adapted.aclose()
        get_settings.cache_clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", ["image", "video"])
async def test_toapis_lookup_uses_documented_client_business_id_status_endpoint(
    monkeypatch, media_type
):
    monkeypatch.setenv("TOAPIS_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(
            200,
            headers={"x-request-id": "provider-request-1"},
            json={"id": "provider-task-1", "status": "processing"},
        )

    provider = ToApisProvider(transport=httpx.MockTransport(handler))
    adapted = adapt_generation_provider(provider, media_type)
    try:
        assert adapted.supports_lookup is True
        assert adapted.supports_idempotent_submit is False
        state = await adapted.lookup("client-business-1")
        assert state["id"] == "provider-task-1"
        assert state["provider_request_id"] == "provider-request-1"
        assert calls == [f"/v1/{media_type}s/generations/client-business-1"]
    finally:
        await adapted.aclose()
        get_settings.cache_clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [404, 503])
async def test_toapis_lookup_distinguishes_missing_from_provider_outage(monkeypatch, status_code):
    monkeypatch.setenv("TOAPIS_KEY", "test-key")
    from app.core.config import get_settings

    get_settings.cache_clear()
    provider = ToApisProvider(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(status_code, json={"message": "unavailable"})
        )
    )
    adapted = adapt_generation_provider(provider, "video")
    try:
        if status_code == 404:
            assert await adapted.lookup("client-business-1") is None
        else:
            with pytest.raises(ToApisError) as exc_info:
                await adapted.lookup("client-business-1")
            assert exc_info.value.status_code == 503
    finally:
        await adapted.aclose()
        get_settings.cache_clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["toapis", "volcengine"])
@pytest.mark.parametrize("body", [b"not-json", b"[]", b"null"])
async def test_successful_http_with_invalid_body_preserves_uncertain_submission(
    monkeypatch, provider_name, body,
):
    from app.core.config import get_settings

    monkeypatch.setenv("TOAPIS_KEY", "test-key")
    monkeypatch.setenv("VOLCENGINE_SPEECH_API_KEY", "test-key")
    get_settings.cache_clear()
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=body, headers={"x-request-id": "bad-body-request"})
    )
    provider = (
        ToApisProvider(transport=transport)
        if provider_name == "toapis" else VolcengineAudioProvider(transport=transport)
    )
    adapted = adapt_generation_provider(provider, "image" if provider_name == "toapis" else "audio")
    try:
        with pytest.raises((ToApisError, VolcengineAudioError)) as captured:
            await adapted.submit({}, client_request_id="stable-request")
        assert captured.value.retryable
        assert captured.value.request_id == "bad-body-request"
    finally:
        await adapted.aclose()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_audio_successful_http_without_business_status_is_unknown(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("VOLCENGINE_SPEECH_API_KEY", "test-key")
    get_settings.cache_clear()
    provider = VolcengineAudioProvider(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
    )
    try:
        with pytest.raises(VolcengineAudioError) as captured:
            await provider.synthesize({}, client_request_id="stable-request")
        assert captured.value.retryable
        assert captured.value.request_id == "stable-request"
    finally:
        await provider.client.aclose()
        get_settings.cache_clear()
