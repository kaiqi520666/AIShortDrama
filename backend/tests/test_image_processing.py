from io import BytesIO

import httpx
import pytest
from PIL import Image

import app.services.image_processing as image_processing
from app.services.image_processing import (
    OUTFIT_BOARD_CELL_HEIGHT,
    OUTFIT_BOARD_CELL_WIDTH,
    OutfitBoardDownloadError,
    download_outfit_board_images,
    normalize_image,
)


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


def image_bytes(image_format: str) -> bytes:
    output = BytesIO()
    Image.new("RGBA", (3, 2), (20, 40, 60, 128)).save(output, image_format)
    return output.getvalue()


def test_normalizes_image_and_removes_trailing_data():
    trailing = b"unexpected-data-after-iend"
    normalized = normalize_image(BytesIO(image_bytes("PNG") + trailing), "image/png")
    content = normalized.stream.read()

    assert trailing not in content
    assert (normalized.width, normalized.height, normalized.size) == (3, 2, len(content))
    with Image.open(BytesIO(content)) as image:
        image.verify()


def test_rejects_invalid_image():
    with pytest.raises(ValueError, match="图片文件已损坏或无法解析"):
        normalize_image(BytesIO(b"not-an-image"), "image/png")


def test_reencodes_mismatched_content_type():
    normalized = normalize_image(BytesIO(image_bytes("PNG")), "image/jpeg")

    with Image.open(normalized.stream) as image:
        assert image.format == "JPEG"
        assert image.size == (3, 2)


@pytest.mark.asyncio
async def test_remote_outfit_image_rejects_large_content_length():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"content-length": "6", "content-type": "image/png"},
            stream=ChunkStream([b"small"]),
        )
    )

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(OutfitBoardDownloadError, match="单张图片不能超过"):
            await download_outfit_board_images(
                ["https://upstream.test/image.png"], client, max_bytes=5, max_total_bytes=30
            )


@pytest.mark.asyncio
async def test_remote_outfit_image_rejects_stream_limit_and_closes_tempfile(monkeypatch):
    streams = []

    def temporary_file():
        stream = BytesIO()
        streams.append(stream)
        return stream

    monkeypatch.setattr(image_processing.tempfile, "TemporaryFile", temporary_file)
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={"content-length": "3", "content-type": "image/png"},
            stream=ChunkStream([b"123", b"456"]),
        )
    )

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(OutfitBoardDownloadError, match="单张图片不能超过"):
            await download_outfit_board_images(
                ["https://upstream.test/image.png"], client, max_bytes=5, max_total_bytes=30
            )

    assert streams[0].closed


@pytest.mark.asyncio
async def test_remote_outfit_image_rejects_decompression_bomb(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=image_bytes("PNG"))
    )

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(OutfitBoardDownloadError, match="像素尺寸过大"):
            await download_outfit_board_images(["https://upstream.test/image.png"], client)


@pytest.mark.asyncio
async def test_remote_outfit_image_downscales_before_retaining_copy():
    source = BytesIO()
    Image.new("RGB", (OUTFIT_BOARD_CELL_WIDTH * 2, OUTFIT_BOARD_CELL_HEIGHT * 2), "white").save(
        source, "PNG"
    )
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=source.getvalue()))

    async with httpx.AsyncClient(transport=transport) as client:
        images = await download_outfit_board_images(["https://upstream.test/image.png"], client)

    try:
        assert images[0].width <= OUTFIT_BOARD_CELL_WIDTH
        assert images[0].height <= OUTFIT_BOARD_CELL_HEIGHT
    finally:
        images[0].close()
