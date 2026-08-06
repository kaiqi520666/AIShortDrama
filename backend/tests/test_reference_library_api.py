import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.api.routes import reference_library as reference_library_route
from app.core.database import SessionLocal
from app.main import app
from app.models import Asset, Character, Garment, OutfitModel


class FakeStorage:
    async def store_upload(self, object_key, stream, content_type):
        return f"https://cdn.example.com/{object_key}"


def png_bytes():
    output = BytesIO()
    Image.new("RGB", (6, 8), (80, 100, 120)).save(output, "PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_reference_libraries_separate_system_and_user_content(
    monkeypatch,
    override_business_user,
):
    monkeypatch.setattr(reference_library_route, "OssStorage", FakeStorage)
    monkeypatch.setattr(
        reference_library_route,
        "register_virtual_character",
        lambda *_: async_value({
            "provider": "toapis",
            "type": "private-avatar",
            "group_id": "pg_test",
            "asset_id": "pa_test",
            "asset_url": "asset://pa_test",
            "status": "active",
        }),
    )
    created_ids = []
    system_garment = Garment(
        name="系统标准服饰",
        image_url="https://cdn.example.com/system/garment.png",
        width=6,
        height=8,
    )
    system_character = Character(
        name="系统虚拟角色",
        image_url="https://cdn.example.com/system/character.png",
        width=6,
        height=8,
    )
    async with SessionLocal() as db:
        db.add_all([system_garment, system_character])
        await db.commit()
        await db.refresh(system_garment)
        await db.refresh(system_character)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        initial_models = (await client.get("/api/outfit-models")).json()["data"]
        initial_characters = (await client.get("/api/characters")).json()["data"]
        initial_garments = (await client.get("/api/garments")).json()["data"]
        model = (
            await client.post(
                "/api/outfit-models",
                files={"file": ("我的模特.png", png_bytes(), "image/png")},
            )
        ).json()["data"]
        character = (
            await client.post(
                "/api/characters",
                files={"file": ("我的角色.png", png_bytes(), "image/png")},
            )
        ).json()["data"]
        garment = (
            await client.post(
                "/api/garments",
                files={"file": ("我的服饰.png", png_bytes(), "image/png")},
            )
        ).json()["data"]
        registered_system_character = (
            await client.post(f"/api/characters/{system_character.id}/register")
        ).json()["data"]

    created_ids = [uuid.UUID(model["id"]), uuid.UUID(character["id"]), uuid.UUID(garment["id"])]
    assert len([item for item in initial_models if item["source"] == "system"]) == 25
    assert all(item["resource_type"] == "model" for item in initial_models)
    assert all(item["resource_type"] == "character" for item in initial_characters)
    assert ("系统标准服饰", "system") in [
        (item["name"], item["source"]) for item in initial_garments
    ]
    assert all(item["resource_type"] == "garment" for item in initial_garments)
    assert model["resource_type"] == "model" and model["source"] == "user"
    assert character["resource_type"] == "character" and character["source"] == "user"
    assert character["metadata"]["seedance"]["asset_url"] == "asset://pa_test"
    assert registered_system_character["metadata"]["seedance"]["status"] == "active"
    assert garment["resource_type"] == "garment" and garment["source"] == "user"
    assert (model["width"], model["height"]) == (6, 8)
    async with SessionLocal() as db:
        assert (await db.get(OutfitModel, created_ids[0])).user_id == override_business_user
        assert (await db.get(Character, created_ids[1])).user_id == override_business_user
        assert (await db.get(Garment, created_ids[2])).user_id == override_business_user


async def async_value(value):
    return value


@pytest.mark.asyncio
async def test_create_character_from_existing_asset(monkeypatch, override_business_user):
    monkeypatch.setattr(
        reference_library_route,
        "register_virtual_character",
        lambda *_: async_value({
            "provider": "toapis",
            "type": "private-avatar",
            "group_id": "pg_asset",
            "asset_id": "pa_asset",
            "asset_url": "asset://pa_asset",
            "status": "active",
        }),
    )
    async with SessionLocal() as db:
        asset = Asset(
            user_id=override_business_user,
            media_type="image",
            source_type="upload",
            name="素材角色.png",
            object_key="assets/character.png",
            url="https://cdn.example.com/assets/character.png",
            width=600,
            height=800,
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        asset_id = asset.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/characters/from-asset/{asset_id}")
    payload = response.json()["data"]
    character_id = uuid.UUID(payload["id"])

    assert payload["resource_type"] == "character"
    assert payload["name"] == "素材角色"
    assert payload["metadata"]["source_asset_id"] == str(asset_id)
    assert payload["metadata"]["seedance"]["status"] == "active"
    async with SessionLocal() as db:
        character = await db.get(Character, character_id)
        assert character.user_id == override_business_user
        assert character.image_url == "https://cdn.example.com/assets/character.png"
