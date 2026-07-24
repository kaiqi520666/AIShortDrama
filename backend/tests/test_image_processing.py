from io import BytesIO

import pytest
from PIL import Image

from app.services.image_processing import normalize_image


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


def test_rejects_mismatched_content_type():
    with pytest.raises(ValueError, match="图片格式与文件内容不匹配"):
        normalize_image(BytesIO(image_bytes("PNG")), "image/jpeg")
