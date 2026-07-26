import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.api.routes import reference_library as reference_library_route
from app.core.database import SessionLocal
from app.main import app
from app.models import Character, OutfitModel


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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        initial_models = (await client.get("/api/outfit-models")).json()["data"]
        initial_characters = (await client.get("/api/characters")).json()["data"]
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

    created_ids = [uuid.UUID(model["id"]), uuid.UUID(character["id"])]
    try:
        assert len([item for item in initial_models if item["source"] == "system"]) == 25
        assert all(item["resource_type"] == "model" for item in initial_models)
        assert all(item["resource_type"] == "character" for item in initial_characters)
        assert model["resource_type"] == "model" and model["source"] == "user"
        assert character["resource_type"] == "character" and character["source"] == "user"
        assert (model["width"], model["height"]) == (6, 8)
        async with SessionLocal() as db:
            assert (await db.get(OutfitModel, created_ids[0])).user_id == override_business_user
            assert (await db.get(Character, created_ids[1])).user_id == override_business_user
    finally:
        async with SessionLocal() as db:
            model_row = await db.get(OutfitModel, created_ids[0])
            character_row = await db.get(Character, created_ids[1])
            if model_row:
                await db.delete(model_row)
            if character_row:
                await db.delete(character_row)
            await db.commit()
