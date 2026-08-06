from io import BytesIO

import httpx
import pytest

import app.services.storage as storage_module
from app.services.storage import (
    AUDIO_MAX_BYTES,
    IMAGE_MAX_BYTES,
    VIDEO_MAX_BYTES,
    MediaSizeLimitError,
    OssStorage,
)


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


class FakeBucket:
    def __init__(self):
        self.uploads = []
        self.deleted = []

    def put_object(self, object_key, stream, headers):
        self.uploads.append((object_key, stream.read(), headers))

    def delete_object(self, object_key):
        self.deleted.append(object_key)


def make_storage():
    storage = object.__new__(OssStorage)
    storage.bucket = FakeBucket()
    storage.public_base_url = "https://cdn.test"
    return storage


def mock_remote(monkeypatch, response):
    client_class = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _request: response)
    monkeypatch.setattr(
        storage_module.httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=transport, **kwargs),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "limit"),
    [("image", IMAGE_MAX_BYTES), ("video", VIDEO_MAX_BYTES), ("audio", AUDIO_MAX_BYTES)],
)
async def test_remote_media_rejects_large_content_length(monkeypatch, kind, limit):
    response = httpx.Response(
        200,
        headers={"content-length": str(limit + 1), "content-type": f"{kind}/mp4"},
        stream=ChunkStream([b"small"]),
    )
    mock_remote(monkeypatch, response)
    storage = make_storage()

    with pytest.raises(MediaSizeLimitError, match="不能超过"):
        if kind == "image":
            await storage.store_remote_images("task", ["https://upstream.test/file.png"])
        elif kind == "video":
            await storage.store_remote_videos("task", ["https://upstream.test/file.mp4"])
        else:
            await storage.store_remote_audios("task", ["https://upstream.test/file.mp3"], "mp3")

    assert storage.bucket.uploads == []


@pytest.mark.asyncio
async def test_remote_media_rejects_stream_over_limit_and_closes_tempfile(monkeypatch):
    monkeypatch.setattr(storage_module, "IMAGE_MAX_BYTES", 5)
    response = httpx.Response(
        200,
        headers={"content-length": "3", "content-type": "image/png"},
        stream=ChunkStream([b"123", b"456"]),
    )
    mock_remote(monkeypatch, response)
    streams = []

    def temporary_file():
        stream = BytesIO()
        streams.append(stream)
        return stream

    monkeypatch.setattr(storage_module.tempfile, "TemporaryFile", temporary_file)
    storage = make_storage()

    with pytest.raises(MediaSizeLimitError, match="图片文件不能超过"):
        await storage.store_remote_images("task", ["https://upstream.test/file.png"])

    assert streams[0].closed
    assert storage.bucket.uploads == []


@pytest.mark.asyncio
async def test_remote_image_is_streamed_to_oss(monkeypatch):
    response = httpx.Response(
        200,
        headers={"content-type": "image/webp"},
        stream=ChunkStream([b"image", b"-data"]),
    )
    mock_remote(monkeypatch, response)
    storage = make_storage()

    result = await storage.store_remote_images("task", ["https://upstream.test/file"])

    assert result == ["https://cdn.test/generations/images/task-1.webp"]
    assert storage.bucket.uploads == [
        ("generations/images/task-1.webp", b"image-data", {"Content-Type": "image/webp"})
    ]


@pytest.mark.asyncio
async def test_audio_bytes_respects_size_limit(monkeypatch):
    monkeypatch.setattr(storage_module, "AUDIO_MAX_BYTES", 5)
    storage = make_storage()

    with pytest.raises(MediaSizeLimitError, match="音频文件不能超过"):
        await storage.store_audio_bytes("task", b"123456", "mp3")

    assert storage.bucket.uploads == []


@pytest.mark.asyncio
async def test_delete_object_removes_uploaded_key():
    storage = make_storage()

    await storage.delete_object("generations/images/orphan.jpg")

    assert storage.bucket.deleted == ["generations/images/orphan.jpg"]
