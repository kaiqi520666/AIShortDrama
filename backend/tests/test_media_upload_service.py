from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.services.media_upload import MediaUploadService, StoredMedia


class FakeStorage:
    def __init__(self):
        self.uploaded = None
        self.deleted = []

    async def store_upload(self, object_key, stream, content_type):
        self.uploaded = (object_key, stream.read(), content_type)
        return f"https://cdn.example.com/{object_key}"

    async def delete_object(self, object_key):
        self.deleted.append(object_key)


def png_bytes():
    output = BytesIO()
    Image.new("RGB", (6, 8), "#345678").save(output, "PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_store_normalizes_images_and_closes_upload():
    storage = FakeStorage()
    upload = UploadFile(
        BytesIO(png_bytes()),
        filename="source.jpg",
        size=len(png_bytes()),
        headers=Headers({"content-type": "image/png"}),
    )
    service = MediaUploadService(lambda: storage)

    stored = await service.store(upload, "image", "library/characters")

    assert isinstance(stored, StoredMedia)
    assert stored.width == 6 and stored.height == 8
    assert stored.content_type == "image/png"
    assert storage.uploaded[0].startswith("library/characters/")
    with Image.open(BytesIO(storage.uploaded[1])) as image:
        assert image.format == "PNG"
    assert upload.file.closed


@pytest.mark.asyncio
async def test_store_rejects_oversized_file_before_storage():
    storage = FakeStorage()
    upload = UploadFile(
        BytesIO(b"1234"),
        filename="source.mp4",
        size=4,
        headers=Headers({"content-type": "video/mp4"}),
    )
    service = MediaUploadService(lambda: storage)
    rules = {"video": {"max_size": 3, "content_types": {"video/mp4": ".mp4"}}}

    with pytest.raises(ValueError, match="不能超过 3B"):
        await service.store(upload, "video", "uploads/videos", rules=rules)

    assert storage.uploaded is None
    assert upload.file.closed


@pytest.mark.asyncio
async def test_delete_uses_storage_bound_to_stored_media():
    storage = FakeStorage()
    stored = StoredMedia("key", "url", "image/png", 1, None, None, storage)

    await MediaUploadService.delete(stored)

    assert storage.deleted == ["key"]
