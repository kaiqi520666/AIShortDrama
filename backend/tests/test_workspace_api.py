import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import SessionLocal
from app.main import app
from app.models import Asset, Workspace


@pytest.mark.asyncio
async def test_workspace_crud_duplicate_and_canvas_isolation(override_business_user):
    asset_id = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = (await client.post("/api/workspaces", json={"name": "测试工作台"})).json()["data"]
        workspace_id = uuid.UUID(created["id"])
        canvas = {
            "schema_version": 1,
            "nodes": [{"id": "text-1", "type": "text", "position": {"x": 10, "y": 20}, "data": {}}],
            "edges": [],
            "groups": [],
            "sequence": 2,
            "group_sequence": 1,
            "viewport": {"x": 12, "y": 14, "zoom": 0.8},
        }
        saved = (await client.put(f"/api/workspaces/{workspace_id}/canvas", json=canvas)).json()
        loaded = (await client.get(f"/api/workspaces/{workspace_id}")).json()["data"]
        renamed = (await client.patch(f"/api/workspaces/{workspace_id}", json={"name": "新名称"})).json()
        duplicate = (await client.post(f"/api/workspaces/{workspace_id}/duplicate")).json()["data"]
        duplicate_id = uuid.UUID(duplicate["id"])
        async with SessionLocal() as db:
            asset = Asset(
                    user_id=override_business_user,
                workspace_id=workspace_id,
                node_id="image-asset-test",
                media_type="image",
                source_type="generation",
                name="保留资产",
                url="https://example.com/asset.png",
            )
            db.add(asset)
            await db.commit()
            await db.refresh(asset)
            asset_id = asset.id
        await client.delete(f"/api/workspaces/{workspace_id}")
        retained_assets = (
            await client.get("/api/assets", params={"workspace_id": str(workspace_id)})
        ).json()["data"]

    try:
        assert saved["code"] == 0
        assert loaded["canvas"] == canvas
        assert renamed["data"]["name"] == "新名称"
        assert duplicate["canvas"] == canvas
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            listed = (await client.get("/api/workspaces")).json()["data"]
        assert str(workspace_id) not in {item["id"] for item in listed}
        assert str(duplicate_id) in {item["id"] for item in listed}
        assert str(asset_id) in {item["id"] for item in retained_assets}
    finally:
        async with SessionLocal() as db:
            asset = await db.get(Asset, asset_id) if asset_id else None
            if asset:
                await db.delete(asset)
            for item_id in (workspace_id, duplicate_id):
                item = await db.get(Workspace, item_id)
                if item:
                    await db.delete(item)
            await db.commit()
