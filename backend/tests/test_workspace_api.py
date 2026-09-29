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
        created = (
            await client.post(
                "/api/workspaces",
                json={"name": "测试工作台", "workspace_type": "ecommerce"},
            )
        ).json()["data"]
        workspace_id = uuid.UUID(created["id"])
        canvas = {
            "version": created["version"],
            "schema_version": 1,
            "nodes": [{"id": "text-1", "type": "text", "position": {"x": 10, "y": 20}, "data": {}}],
            "edges": [],
            "groups": [],
            "sequence": 2,
            "group_sequence": 1,
            "viewport": {"x": 12, "y": 14, "zoom": 0.8},
        }
        save_response = await client.put(f"/api/workspaces/{workspace_id}/canvas", json=canvas)
        saved = save_response.json()
        stale_canvas = {**canvas, "nodes": []}
        stale_response = await client.put(
            f"/api/workspaces/{workspace_id}/canvas", json=stale_canvas
        )
        async with SessionLocal() as db:
            workspace = await db.get(Workspace, workspace_id)
            workspace.thumbnail_url = "https://example.com/latest.webp"
            await db.commit()
        loaded = (await client.get(f"/api/workspaces/{workspace_id}")).json()["data"]
        listed_before_delete = (await client.get("/api/workspaces")).json()["data"]
        renamed = (
            await client.patch(f"/api/workspaces/{workspace_id}", json={"name": "新名称"})
        ).json()
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

    assert saved["code"] == 0
    assert saved["data"]["version"] == created["version"] + 1
    assert stale_response.status_code == 409
    assert stale_response.json()["message"] == "画布已在其他页面更新，请刷新后继续"
    assert created["thumbnail_url"] is None
    assert created["workspace_type"] == "ecommerce"
    assert loaded["canvas"] == {key: value for key, value in canvas.items() if key != "version"}
    assert loaded["version"] == saved["data"]["version"]
    listed_workspace = next(
        item for item in listed_before_delete if item["id"] == str(workspace_id)
    )
    assert listed_workspace["thumbnail_url"] == "https://example.com/latest.webp"
    assert renamed["data"]["name"] == "新名称"
    assert duplicate["canvas"] == {key: value for key, value in canvas.items() if key != "version"}
    assert duplicate["thumbnail_url"] == "https://example.com/latest.webp"
    assert duplicate["workspace_type"] == "ecommerce"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = (await client.get("/api/workspaces")).json()["data"]
    assert str(workspace_id) not in {item["id"] for item in listed}
    assert str(duplicate_id) in {item["id"] for item in listed}
    assert str(asset_id) in {item["id"] for item in retained_assets}


@pytest.mark.asyncio
@pytest.mark.parametrize("workspace_type", ["general", "ecommerce"])
async def test_workspace_create_accepts_supported_type(
    override_business_user, workspace_type
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = (
            await client.post(
                "/api/workspaces",
                json={"name": "类型测试", "workspace_type": workspace_type},
            )
        ).json()["data"]
        await client.delete(f"/api/workspaces/{created['id']}")

    assert created["workspace_type"] == workspace_type


@pytest.mark.asyncio
@pytest.mark.parametrize("workspace_type", ["unknown", "drama"])
async def test_workspace_create_rejects_invalid_type(workspace_type):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/workspaces",
            json={"name": "错误类型", "workspace_type": workspace_type},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_workspace_uses_not_found_envelope(override_business_user):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/workspaces/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"code": 1, "message": "工作台不存在", "data": None, "error_key": "not_found", "error_params": {}}
