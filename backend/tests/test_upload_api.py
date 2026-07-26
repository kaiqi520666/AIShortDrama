import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.api.routes import uploads as uploads_route
from app.core.database import SessionLocal
from app.core.identity import DEFAULT_WORKSPACE_ID
from app.main import app
from app.models import Asset


class FakeStorage:
    uploaded = None

    async def store_upload(self, object_key, stream, content_type):
        self.__class__.uploaded = (object_key, stream.read(), content_type)
        return f"https://cdn.example.com/{object_key}"


def png_bytes():
    output = BytesIO()
    Image.new("RGB", (3, 2), (20, 40, 60)).save(output, "PNG")
    return output.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_type", "filename", "content_type", "content"),
    [
        ("image", "source.png", "image/png", png_bytes()),
        ("video", "source.mp4", "video/mp4", b"video-data"),
    ],
)
async def test_upload_media(monkeypatch, media_type, filename, content_type, content):
    monkeypatch.setattr(uploads_route, "OssStorage", FakeStorage)
    category = "model" if media_type == "image" else "general"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/uploads/{media_type}",
            data={"workspace_id": str(DEFAULT_WORKSPACE_ID), "node_id": f"{media_type}-upload", "category": category},
            files={"file": (filename, content, content_type)},
        )

    payload = response.json()
    try:
        assert payload["code"] == 0
        assert payload["data"]["url"].startswith(f"https://cdn.example.com/uploads/{media_type}s/")
        assert payload["data"]["size"] == len(content)
        assert payload["data"]["category"] == category
        assert FakeStorage.uploaded[1:] == (content, content_type)
        async with SessionLocal() as db:
            asset = await db.get(Asset, uuid.UUID(payload["data"]["id"]))
            assert asset.source_type == "upload"
            assert asset.workspace_id == DEFAULT_WORKSPACE_ID
            assert asset.asset_metadata["category"] == category
    finally:
        if payload.get("data", {}).get("id"):
            async with SessionLocal() as db:
                asset = await db.get(Asset, uuid.UUID(payload["data"]["id"]))
                if asset:
                    await db.delete(asset)
                    await db.commit()


@pytest.mark.asyncio
async def test_reencodes_image_when_declared_format_differs_from_content(monkeypatch):
    monkeypatch.setattr(uploads_route, "OssStorage", FakeStorage)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/uploads/image",
            data={"workspace_id": str(DEFAULT_WORKSPACE_ID), "node_id": "image-mismatch"},
            files={"file": ("source.jpg", png_bytes(), "image/jpeg")},
        )

    payload = response.json()
    try:
        assert payload["code"] == 0
        assert FakeStorage.uploaded[0].endswith(".jpg")
        assert FakeStorage.uploaded[2] == "image/jpeg"
        with Image.open(BytesIO(FakeStorage.uploaded[1])) as uploaded:
            assert uploaded.format == "JPEG"
            assert uploaded.size == (3, 2)
    finally:
        if payload.get("data", {}).get("id"):
            async with SessionLocal() as db:
                asset = await db.get(Asset, uuid.UUID(payload["data"]["id"]))
                if asset:
                    await db.delete(asset)
                    await db.commit()


@pytest.mark.asyncio
async def test_rejects_unsupported_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/uploads/video",
            data={"workspace_id": str(DEFAULT_WORKSPACE_ID), "node_id": "video-invalid"},
            files={"file": ("source.avi", b"video-data", "video/x-msvideo")},
        )

    assert response.json()["message"] == "不支持的视频格式"


@pytest.mark.asyncio
async def test_rejects_oversized_file(monkeypatch):
    monkeypatch.setitem(
        uploads_route.UPLOAD_RULES,
        "image",
        {"max_size": 3, "content_types": {"image/png": ".png"}},
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/uploads/image",
            data={"workspace_id": str(DEFAULT_WORKSPACE_ID), "node_id": "image-large"},
            files={"file": ("source.png", b"large", "image/png")},
        )

    assert response.json()["message"] == "文件不能超过 3B"
