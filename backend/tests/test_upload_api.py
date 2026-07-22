import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import uploads as uploads_route
from app.main import app


class FakeStorage:
    uploaded = None

    async def store_upload(self, object_key, stream, content_type):
        self.__class__.uploaded = (object_key, stream.read(), content_type)
        return f"https://cdn.example.com/{object_key}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_type", "filename", "content_type", "content"),
    [
        ("image", "source.png", "image/png", b"image-data"),
        ("video", "source.mp4", "video/mp4", b"video-data"),
    ],
)
async def test_upload_media(monkeypatch, media_type, filename, content_type, content):
    monkeypatch.setattr(uploads_route, "OssStorage", FakeStorage)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/uploads/{media_type}",
            files={"file": (filename, content, content_type)},
        )

    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["url"].startswith(f"https://cdn.example.com/uploads/{media_type}s/")
    assert payload["data"]["size"] == len(content)
    assert FakeStorage.uploaded[1:] == (content, content_type)


@pytest.mark.asyncio
async def test_rejects_unsupported_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/uploads/video",
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
            files={"file": ("source.png", b"large", "image/png")},
        )

    assert response.json()["message"] == "文件不能超过 3B"
