from collections.abc import Callable, Iterable
from typing import Any, cast

from app.providers.protocols import (
    GenerationProvider,
    PrivateAvatarProvider,
    TextProvider,
)


class ProviderConfigurationError(RuntimeError):
    pass


class GenerationProviderAdapter:
    """Keep provider wire formats while unifying worker entry points and ownership."""

    def __init__(self, provider: Any, media_type: str):
        if media_type not in {"image", "video", "audio"}:
            raise ProviderConfigurationError(f"不支持的生成类型：{media_type}")
        self.provider = provider
        self.media_type = media_type

    @property
    def supports_lookup(self) -> bool:
        from app.providers.toapis import ToApisProvider

        default = (
            isinstance(self.provider, ToApisProvider) and self.media_type in {"image", "video"}
        ) or callable(getattr(self.provider, "lookup", None))
        return bool(getattr(self.provider, "supports_lookup", default))

    @property
    def supports_idempotent_submit(self) -> bool:
        return bool(getattr(self.provider, "supports_idempotent_submit", False))

    async def submit(
        self, payload: dict[str, Any], *, client_request_id: str | None = None
    ) -> dict[str, Any]:
        submit = getattr(self.provider, "submit", None)
        if submit is not None:
            return await submit(payload, client_request_id=client_request_id)
        if self.media_type == "audio":
            from app.providers.volcengine_audio import VolcengineAudioProvider

            if isinstance(self.provider, VolcengineAudioProvider):
                return await self.provider.synthesize(
                    payload, client_request_id=client_request_id
                )
        name = "synthesize" if self.media_type == "audio" else f"submit_{self.media_type}"
        submit = getattr(self.provider, name)
        return await submit(payload)

    async def get_task(self, task_id: str) -> dict[str, Any]:
        fetch = getattr(self.provider, "get_task", None)
        if fetch is None:
            if self.media_type == "audio":
                raise ProviderConfigurationError("同步音频 Provider 不支持任务查询")
            fetch = getattr(self.provider, f"get_{self.media_type}_task")
        return await fetch(task_id)

    async def lookup(self, client_request_id: str) -> dict[str, Any] | None:
        if not self.supports_lookup:
            raise ProviderConfigurationError("Provider 不支持按客户端请求 ID 查询")
        lookup = getattr(self.provider, "lookup", None)
        if lookup is not None:
            return await lookup(client_request_id)
        # ToAPIs documents the same status endpoint for IDs and client_business_id.
        from app.providers.toapis import ToApisError

        try:
            return await self.get_task(client_request_id)
        except ToApisError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def aclose(self) -> None:
        close = getattr(self.provider, "aclose", None)
        if close is not None:
            await close()
        elif getattr(self.provider, "client", None) is not None:
            await self.provider.client.aclose()


def adapt_generation_provider(provider: Any, media_type: str) -> GenerationProvider:
    if isinstance(provider, GenerationProviderAdapter):
        if provider.media_type != media_type:
            raise ProviderConfigurationError("Provider adapter 的生成类型不匹配")
        return provider
    return GenerationProviderAdapter(provider, media_type)


class ProviderRegistry:
    def __init__(self):
        self._factories: dict[tuple[str, str], Callable[[], Any]] = {}

    def register(
        self, provider_name: str, media_types: Iterable[str], factory: Callable[[], Any]
    ) -> None:
        for media_type in media_types:
            self._factories[(provider_name, media_type)] = factory

    def create(self, provider_name: str, media_type: str) -> Any:
        factory = self._factories.get((provider_name, media_type))
        if factory is None:
            raise ProviderConfigurationError(
                f"Provider {provider_name} 不支持类型 {media_type}"
            )
        return factory()

    def create_generation(self, provider_name: str, media_type: str) -> GenerationProvider:
        return adapt_generation_provider(self.create(provider_name, media_type), media_type)


def _create_toapis():
    from app.providers.toapis import ToApisProvider

    return ToApisProvider()


def _create_audio():
    from app.providers.volcengine_audio import VolcengineAudioProvider

    return VolcengineAudioProvider()


def _create_text():
    from app.providers.openai_responses import OpenAIResponsesProvider

    return OpenAIResponsesProvider()


provider_registry = ProviderRegistry()
provider_registry.register("toapis", {"image", "video", "private_avatar"}, _create_toapis)
provider_registry.register("volcengine", {"audio"}, _create_audio)
provider_registry.register("aijws", {"text"}, _create_text)


def create_generation_provider(provider_name: str, media_type: str) -> GenerationProvider:
    return provider_registry.create_generation(provider_name, media_type)


def create_text_provider(provider_name: str = "aijws") -> TextProvider:
    return cast(TextProvider, provider_registry.create(provider_name, "text"))


def create_private_avatar_provider(provider_name: str = "toapis") -> PrivateAvatarProvider:
    return cast(PrivateAvatarProvider, provider_registry.create(provider_name, "private_avatar"))
