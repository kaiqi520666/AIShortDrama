from dataclasses import dataclass
from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from app.core.errors import LocalizedValueError


IMAGE_FORMATS = {
    "image/jpeg": ("JPEG", {"quality": 92, "optimize": True}),
    "image/png": ("PNG", {"compress_level": 6}),
    "image/webp": ("WEBP", {"quality": 92, "method": 4}),
}
@dataclass(frozen=True)
class NormalizedImage:
    stream: BytesIO
    width: int
    height: int
    size: int


def normalize_image(stream, content_type: str) -> NormalizedImage:
    image_format, save_options = IMAGE_FORMATS[content_type]
    stream.seek(0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(stream) as source:
                image = ImageOps.exif_transpose(source)
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise LocalizedValueError("图片像素尺寸过大", error_key="image_dimensions") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise LocalizedValueError("图片文件已损坏或无法解析", error_key="invalid_image") from exc

    if image_format == "JPEG":
        image = image.convert("RGB")
    elif image.mode not in {"L", "LA", "P", "RGB", "RGBA"}:
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    output = BytesIO()
    image.save(output, image_format, **save_options)
    size = output.tell()
    output.seek(0)
    return NormalizedImage(output, image.width, image.height, size)
