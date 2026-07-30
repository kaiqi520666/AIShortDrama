from dataclasses import dataclass
from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


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


def compose_outfit_board(images: list[Image.Image]) -> tuple[BytesIO, int, int]:
    if len(images) != 6:
        raise ValueError("服饰总览图必须包含 6 张图片")

    width, height = 2048, 3640
    gap = 16
    cell_width = (width - gap) // 2
    cell_height = (height - gap * 2) // 3
    board = Image.new("RGB", (width, height), "white")
    for index, source in enumerate(images):
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
        left = (index % 2) * (cell_width + gap) + (cell_width - image.width) // 2
        top = (index // 2) * (cell_height + gap) + (cell_height - image.height) // 2
        board.paste(image, (left, top), image)

    output = BytesIO()
    board.save(output, "JPEG", quality=92, optimize=True)
    output.seek(0)
    return output, width, height


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
        raise ValueError("图片像素尺寸过大") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("图片文件已损坏或无法解析") from exc

    if image_format == "JPEG":
        image = image.convert("RGB")
    elif image.mode not in {"L", "LA", "P", "RGB", "RGBA"}:
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    output = BytesIO()
    image.save(output, image_format, **save_options)
    size = output.tell()
    output.seek(0)
    return NormalizedImage(output, image.width, image.height, size)
