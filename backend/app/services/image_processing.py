from dataclasses import dataclass
from io import BytesIO
import tempfile
import warnings

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.storage import IMAGE_MAX_BYTES


IMAGE_FORMATS = {
    "image/jpeg": ("JPEG", {"quality": 92, "optimize": True}),
    "image/png": ("PNG", {"compress_level": 6}),
    "image/webp": ("WEBP", {"quality": 92, "method": 4}),
}
OUTFIT_BOARD_WIDTH = 2048
OUTFIT_BOARD_HEIGHT = 3640
OUTFIT_BOARD_GAP = 16
OUTFIT_BOARD_CELL_WIDTH = (OUTFIT_BOARD_WIDTH - OUTFIT_BOARD_GAP) // 2
OUTFIT_BOARD_CELL_HEIGHT = (OUTFIT_BOARD_HEIGHT - OUTFIT_BOARD_GAP * 2) // 3
OUTFIT_BOARD_MAX_BYTES = IMAGE_MAX_BYTES * 6


class OutfitBoardDownloadError(RuntimeError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class NormalizedImage:
    stream: BytesIO
    width: int
    height: int
    size: int


def compose_outfit_board(images: list[Image.Image]) -> tuple[BytesIO, int, int]:
    if len(images) != 6:
        raise ValueError("服饰总览图必须包含 6 张图片")

    board = Image.new("RGB", (OUTFIT_BOARD_WIDTH, OUTFIT_BOARD_HEIGHT), "white")
    for index, source in enumerate(images):
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image.thumbnail((OUTFIT_BOARD_CELL_WIDTH, OUTFIT_BOARD_CELL_HEIGHT), Image.Resampling.LANCZOS)
        left = (index % 2) * (OUTFIT_BOARD_CELL_WIDTH + OUTFIT_BOARD_GAP) + (
            OUTFIT_BOARD_CELL_WIDTH - image.width
        ) // 2
        top = (index // 2) * (OUTFIT_BOARD_CELL_HEIGHT + OUTFIT_BOARD_GAP) + (
            OUTFIT_BOARD_CELL_HEIGHT - image.height
        ) // 2
        try:
            board.paste(image, (left, top), image)
        finally:
            image.close()

    output = BytesIO()
    board.save(output, "JPEG", quality=92, optimize=True)
    output.seek(0)
    return output, OUTFIT_BOARD_WIDTH, OUTFIT_BOARD_HEIGHT


def _prepare_outfit_board_image(stream) -> Image.Image:
    stream.seek(0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(stream) as source:
                image = ImageOps.exif_transpose(source)
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise OutfitBoardDownloadError("服饰总览图片像素尺寸过大") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise OutfitBoardDownloadError("服饰总览图片文件已损坏或无法解析") from exc

    image = image.convert("RGBA")
    image.thumbnail((OUTFIT_BOARD_CELL_WIDTH, OUTFIT_BOARD_CELL_HEIGHT), Image.Resampling.LANCZOS)
    return image


async def download_outfit_board_images(
    urls: list[str],
    client: httpx.AsyncClient,
    *,
    max_bytes: int = IMAGE_MAX_BYTES,
    max_total_bytes: int = OUTFIT_BOARD_MAX_BYTES,
) -> list[Image.Image]:
    images = []
    downloaded_total = 0
    try:
        for url in urls:
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_length = response.headers.get("content-length")
                    try:
                        declared_size = int(content_length) if content_length else None
                    except ValueError:
                        declared_size = None
                    if declared_size is not None and declared_size > max_bytes:
                        raise OutfitBoardDownloadError(
                            f"服饰总览单张图片不能超过 {max_bytes // (1024 * 1024)}MB"
                        )
                    if (
                        declared_size is not None
                        and downloaded_total + declared_size > max_total_bytes
                    ):
                        raise OutfitBoardDownloadError(
                            f"服饰总览图片总大小不能超过 {max_total_bytes // (1024 * 1024)}MB"
                        )

                    with tempfile.TemporaryFile() as stream:
                        downloaded = 0
                        async for chunk in response.aiter_bytes():
                            downloaded += len(chunk)
                            downloaded_total += len(chunk)
                            if downloaded > max_bytes:
                                raise OutfitBoardDownloadError(
                                    f"服饰总览单张图片不能超过 {max_bytes // (1024 * 1024)}MB"
                                )
                            if downloaded_total > max_total_bytes:
                                raise OutfitBoardDownloadError(
                                    f"服饰总览图片总大小不能超过 {max_total_bytes // (1024 * 1024)}MB"
                                )
                            stream.write(chunk)
                        images.append(_prepare_outfit_board_image(stream))
            except OutfitBoardDownloadError:
                raise
            except httpx.HTTPError as exc:
                raise OutfitBoardDownloadError("服饰总览源图片读取失败", status_code=502) from exc
    except Exception:
        for image in images:
            image.close()
        raise

    return images


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
