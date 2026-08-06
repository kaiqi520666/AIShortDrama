from collections.abc import Callable
from typing import Any, Protocol

from app.providers.toapis import ToApisError, ToApisProvider


class PrivateAvatarProvider(Protocol):
    async def __aenter__(self) -> "PrivateAvatarProvider": ...

    async def __aexit__(self, *args: Any) -> None: ...

    async def create_private_avatar_group(self, name: str) -> dict[str, Any]: ...

    async def upload_private_avatar(
        self, group_id: str, source_url: str, name: str
    ) -> dict[str, Any]: ...

    async def get_private_avatar(self, asset_id: str) -> dict[str, Any]: ...


def private_avatar_metadata(data: dict[str, Any]) -> dict[str, Any]:
    asset_id = data.get("asset_id") or data.get("id")
    return {
        "provider": "toapis",
        "type": "private-avatar",
        "group_id": data.get("group_id"),
        "asset_id": asset_id,
        "asset_url": data.get("asset_url") or (f"asset://{asset_id}" if asset_id else None),
        "status": str(data.get("status") or "processing").lower(),
    }


class PrivateAvatarService:
    def __init__(self, provider_factory: Callable[[], PrivateAvatarProvider] = ToApisProvider):
        self.provider_factory = provider_factory

    async def register(
        self, name: str, source_url: str, group_id: str | None = None
    ) -> dict[str, Any]:
        async with self.provider_factory() as provider:
            if not group_id:
                group = await provider.create_private_avatar_group(name)
                group_id = group.get("group_id")
            if not group_id:
                raise ToApisError("ToAPIs 未返回虚拟人像组 ID")
            asset = await provider.upload_private_avatar(group_id, source_url, name)
        metadata = private_avatar_metadata({**asset, "group_id": group_id})
        if not metadata["asset_id"]:
            raise ToApisError("ToAPIs 未返回虚拟人像素材 ID")
        return metadata

    async def refresh(self, metadata: dict[str, Any]) -> dict[str, Any]:
        current = private_avatar_metadata(metadata)
        if current["status"] != "processing" or not current["asset_id"]:
            return current
        async with self.provider_factory() as provider:
            state = await provider.get_private_avatar(current["asset_id"])
        return private_avatar_metadata({**current, **state, "group_id": current["group_id"]})
