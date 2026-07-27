import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.api.routes import reference_library as reference_library_route
from app.core.database import SessionLocal
from app.main import app
from app.models import Character, Garment, OutfitModel


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
    created_ids = []
    system_garment = Garment(
        name="系统标准服饰",
        image_url="https://cdn.example.com/system/garment.png",
        width=6,
        height=8,
    )
    async with SessionLocal() as db:
        db.add(system_garment)
        await db.commit()
        await db.refresh(system_garment)
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

    created_ids = [
        uuid.UUID(model["id"]),
        uuid.UUID(character["id"]),
        uuid.UUID(garment["id"]),
        system_garment.id,
    ]
    try:
        assert len([item for item in initial_models if item["source"] == "system"]) == 25
        assert all(item["resource_type"] == "model" for item in initial_models)
        assert all(item["resource_type"] == "character" for item in initial_characters)
        assert ("系统标准服饰", "system") in [
            (item["name"], item["source"]) for item in initial_garments
        ]
        assert all(item["resource_type"] == "garment" for item in initial_garments)
        assert model["resource_type"] == "model" and model["source"] == "user"
        assert character["resource_type"] == "character" and character["source"] == "user"
        assert garment["resource_type"] == "garment" and garment["source"] == "user"
        assert (model["width"], model["height"]) == (6, 8)
        async with SessionLocal() as db:
            assert (await db.get(OutfitModel, created_ids[0])).user_id == override_business_user
            assert (await db.get(Character, created_ids[1])).user_id == override_business_user
            assert (await db.get(Garment, created_ids[2])).user_id == override_business_user
    finally:
        async with SessionLocal() as db:
            model_row = await db.get(OutfitModel, created_ids[0])
            character_row = await db.get(Character, created_ids[1])
            garment_row = await db.get(Garment, created_ids[2])
            system_garment_row = await db.get(Garment, created_ids[3])
            if model_row:
                await db.delete(model_row)
            if character_row:
                await db.delete(character_row)
            if garment_row:
                await db.delete(garment_row)
            if system_garment_row:
                await db.delete(system_garment_row)
            await db.commit()
