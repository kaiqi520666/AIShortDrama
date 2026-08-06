from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
import uuid

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from app.api.routes import assets as assets_module
from app.core.database import SessionLocal
from app.core.errors import ServiceUnavailableError
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import Asset
from app.schemas.asset import ComposeImageBoardRequest


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


class FakeBoardStorage:
    def __init__(self):
        self.deleted = []

    async def store_upload(self, _object_key, _stream, _content_type):
        return "https://example.com/outfit-board.jpg"

    async def delete_object(self, object_key):
        self.deleted.append(object_key)


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
    monkeypatch.setattr(assets_module, "ToApisProvider", FakePrivateAvatarProvider)
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

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            registered = (
                await client.post(
                    f"/api/assets/{asset_id}/private-avatar",
                    json={"group_id": "pg_character"},
                )
            ).json()
            FakePrivateAvatarProvider.status = "active"
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
    finally:
        FakePrivateAvatarProvider.status = "processing"


@pytest.mark.asyncio
async def test_compose_outfit_board(monkeypatch, override_business_user):
    asset_ids = []
    image_buffer = BytesIO()
    Image.new("RGB", (120, 220), "#d9e7ff").save(image_buffer, "PNG")
    image_bytes = image_buffer.getvalue()

    def upstream(_request):
        return httpx.Response(200, content=image_bytes, headers={"Content-Type": "image/png"})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        assets_module.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(upstream), **kwargs),
    )
    monkeypatch.setattr(assets_module, "OssStorage", FakeBoardStorage)

    async with SessionLocal() as db:
        for index in range(6):
            asset = Asset(
                user_id=override_business_user,
                workspace_id=DEFAULT_WORKSPACE_ID,
                media_type="image",
                source_type="generation",
                name=f"穿搭参考 {index + 1}",
                url=f"https://example.com/source-{index + 1}.png",
            )
            db.add(asset)
            await db.flush()
            asset_ids.append(str(asset.id))
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/assets/compose-board",
            json={
                "workspace_id": str(DEFAULT_WORKSPACE_ID),
                "node_id": "outfit-1",
                "asset_ids": asset_ids,
            },
        )

    payload = response.json()["data"]
    assert response.status_code == 200
    assert payload["width"] == 2048
    assert payload["height"] == 3640
    assert payload["metadata"] == {
        "type": "outfit-board",
        "source_asset_ids": asset_ids,
        "layout": "2x3",
        "aspect_ratio": "9:16",
    }


@pytest.mark.asyncio
async def test_compose_outfit_board_removes_uploaded_object_when_database_commit_fails(monkeypatch):
    image_buffer = BytesIO()
    Image.new("RGB", (120, 220), "#d9e7ff").save(image_buffer, "PNG")
    image_bytes = image_buffer.getvalue()
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    source_assets = [
        Asset(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            media_type="image",
            source_type="generation",
            name=f"穿搭参考 {index + 1}",
            url=f"https://example.com/source-{index + 1}.png",
        )
        for index in range(6)
    ]
    storage = FakeBoardStorage()

    class FailedCommitDb:
        rolled_back = False

        async def scalars(self, _query):
            return SimpleNamespace(all=lambda: source_assets)

        def add(self, _board):
            pass

        async def commit(self):
            raise RuntimeError("database unavailable")

        async def rollback(self):
            self.rolled_back = True

    def upstream(_request):
        return httpx.Response(200, content=image_bytes, headers={"Content-Type": "image/png"})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        assets_module.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(upstream), **kwargs),
    )
    monkeypatch.setattr(assets_module, "OssStorage", lambda: storage)
    db = FailedCommitDb()

    with pytest.raises(ServiceUnavailableError, match="服饰总览图服务暂时不可用"):
        await assets_module.compose_board(
            ComposeImageBoardRequest(
                workspace_id=str(workspace_id),
                node_id="outfit-1",
                asset_ids=[str(asset.id) for asset in source_assets],
            ),
            db,
            user_id,
        )
    assert db.rolled_back
    assert len(storage.deleted) == 1
