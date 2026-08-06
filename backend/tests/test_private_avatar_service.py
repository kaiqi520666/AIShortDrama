import pytest

from app.services.private_avatar import PrivateAvatarService


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.status = "active"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def create_private_avatar_group(self, name):
        self.calls.append(("group", name))
        return {"group_id": "group-1"}

    async def upload_private_avatar(self, group_id, source_url, name):
        self.calls.append(("upload", group_id, source_url, name))
        return {"asset_id": "avatar-1", "status": "processing"}

    async def get_private_avatar(self, asset_id):
        self.calls.append(("refresh", asset_id))
        return {"asset_id": asset_id, "status": self.status}


@pytest.mark.asyncio
async def test_register_injects_provider_and_normalizes_metadata():
    provider = FakeProvider()
    service = PrivateAvatarService(lambda: provider)

    result = await service.register("角色", "https://cdn.example.com/role.png")

    assert result == {
        "provider": "toapis",
        "type": "private-avatar",
        "group_id": "group-1",
        "asset_id": "avatar-1",
        "asset_url": "asset://avatar-1",
        "status": "processing",
    }
    assert provider.calls == [
        ("group", "角色"),
        ("upload", "group-1", "https://cdn.example.com/role.png", "角色"),
    ]


@pytest.mark.asyncio
async def test_refresh_only_queries_processing_avatar():
    provider = FakeProvider()
    service = PrivateAvatarService(lambda: provider)
    metadata = {
        "group_id": "group-1",
        "asset_id": "avatar-1",
        "status": "processing",
    }

    result = await service.refresh(metadata)

    assert result["status"] == "active"
    assert result["asset_url"] == "asset://avatar-1"
    assert provider.calls == [("refresh", "avatar-1")]


@pytest.mark.asyncio
async def test_refresh_skips_completed_avatar():
    provider = FakeProvider()
    service = PrivateAvatarService(lambda: provider)

    result = await service.refresh({"asset_id": "avatar-1", "status": "active"})

    assert result["status"] == "active"
    assert provider.calls == []
