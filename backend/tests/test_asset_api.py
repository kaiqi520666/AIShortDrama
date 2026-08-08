from datetime import datetime, timezone

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from app.api.routes import assets as assets_module
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import Asset
from app.services.private_avatar import PrivateAvatarService


class FakePrivateAvatarProvider:
    status = "processing"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def create_private_avatar_group(self, _name):
        return {"group_id": "pg_created"}

    async def upload_private_avatar(self, group_id, _source_url, _name):
        return {"asset_id": "pa_storyboard", "group_id": group_id, "status": "processing"}

    async def get_private_avatar(self, _asset_id):
        return {"asset_id": "pa_storyboard", "status": self.status}


@pytest.mark.asyncio
async def test_list_assets_supports_pagination(override_business_user):
    asset_ids = []
    async with SessionLocal() as db:
        for index in range(3):
            asset = Asset(
                user_id=override_business_user,
                workspace_id=DEFAULT_WORKSPACE_ID,
                media_type="audio",
                source_type="upload",
                name=f"分页资产 {index + 1}",
                url=f"https://example.com/page-{index + 1}.mp3",
                created_at=datetime(2099, 1, 3 - index, tzinfo=timezone.utc),
            )
            db.add(asset)
            await db.flush()
            asset_ids.append(asset.id)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/assets",
            params={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "type": "audio",
                "limit": 2,
                "offset": 1,
            },
        )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [
        str(asset_ids[1]),
        str(asset_ids[2]),
    ]


@pytest.mark.asyncio
async def test_filter_rename_and_delete_asset(override_business_user):
    asset_ids = []
    async with SessionLocal() as db:
        scoped = Asset(
            user_id=override_business_user,
            workspace_id=DEFAULT_WORKSPACE_ID,
            media_type="image",
            source_type="upload",
            name="原名称",
            url="https://example.com/scoped.png",
        )
        global_asset = Asset(
            user_id=override_business_user,
            workspace_id=None,
            media_type="image",
            source_type="upload",
            name="其他资产",
            url="https://example.com/global.png",
        )
        db.add_all([scoped, global_asset])
        await db.commit()
        await db.refresh(scoped)
        await db.refresh(global_asset)
        asset_ids = [scoped.id, global_asset.id]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = (
            await client.get("/api/assets", params={"workspace_id": str(DEFAULT_WORKSPACE_ID)})
        ).json()["data"]
        renamed = (
            await client.patch(f"/api/assets/{asset_ids[0]}", json={"name": " 新名称 "})
        ).json()
        deleted = (await client.delete(f"/api/assets/{asset_ids[0]}")).json()
        remaining = (
            await client.get("/api/assets", params={"workspace_id": str(DEFAULT_WORKSPACE_ID)})
        ).json()["data"]

    assert str(asset_ids[0]) in {item["id"] for item in listed}
    assert str(asset_ids[1]) not in {item["id"] for item in listed}
    assert renamed["data"]["name"] == "新名称"
    assert deleted["data"]["id"] == str(asset_ids[0])
    assert str(asset_ids[0]) not in {item["id"] for item in remaining}


@pytest.mark.asyncio
async def test_stream_asset_forwards_range(monkeypatch, override_business_user):
    asset_id = None
    async with SessionLocal() as db:
        asset = Asset(
            user_id=override_business_user,
            workspace_id=DEFAULT_WORKSPACE_ID,
            media_type="audio",
            source_type="upload",
            name="测试音频",
            url="https://example.com/audio.mp3",
            mime_type="audio/mpeg",
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        asset_id = asset.id

    def upstream(request):
        assert request.headers["range"] == "bytes=0-4"
        return httpx.Response(
            206,
            stream=httpx.ByteStream(b"audio"),
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": "5",
                "Content-Range": "bytes 0-4/10",
                "Content-Type": "audio/mpeg",
            },
        )

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        assets_module.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(upstream), **kwargs),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/assets/{asset_id}/content",
            headers={"Range": "bytes=0-4"},
        )

    assert response.status_code == 206
    assert response.content == b"audio"
    assert response.headers["content-range"] == "bytes 0-4/10"
    assert response.headers["content-type"].startswith("audio/mpeg")


@pytest.mark.asyncio
async def test_register_and_refresh_storyboard_private_avatar(monkeypatch, override_business_user):
    provider = FakePrivateAvatarProvider()
    monkeypatch.setattr(
        assets_module,
        "get_private_avatar_service",
        lambda: PrivateAvatarService(lambda: provider),
    )
    asset_id = None
    async with SessionLocal() as db:
        asset = Asset(
            user_id=override_business_user,
            workspace_id=DEFAULT_WORKSPACE_ID,
            media_type="image",
            source_type="generation",
            name="UGC 分镜板",
            url="https://example.com/storyboard.png",
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        asset_id = asset.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        registered = (
            await client.post(
                f"/api/assets/{asset_id}/private-avatar",
                json={"group_id": "pg_character"},
            )
        ).json()
        provider.status = "active"
        refreshed = (
            await client.post(
                f"/api/assets/{asset_id}/private-avatar",
                json={"group_id": "pg_character"},
            )
        ).json()

    assert registered["data"]["metadata"]["seedance"]["status"] == "processing"
    assert refreshed["data"]["metadata"]["seedance"] == {
        "provider": "toapis",
        "type": "private-avatar",
        "group_id": "pg_character",
        "asset_id": "pa_storyboard",
        "asset_url": "asset://pa_storyboard",
        "status": "active",
    }
