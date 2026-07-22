import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID, LOCAL_USER_ID
from app.main import app
from app.models import Asset


@pytest.mark.asyncio
async def test_filter_rename_and_delete_asset():
    asset_ids = []
    async with SessionLocal() as db:
        scoped = Asset(
            user_id=LOCAL_USER_ID,
            workspace_id=DEFAULT_WORKSPACE_ID,
            media_type="image",
            source_type="upload",
            name="原名称",
            url="https://example.com/scoped.png",
        )
        global_asset = Asset(
            user_id=LOCAL_USER_ID,
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

    try:
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
    finally:
        async with SessionLocal() as db:
            for asset_id in asset_ids:
                asset = await db.get(Asset, asset_id)
                if asset:
                    await db.delete(asset)
            await db.commit()
