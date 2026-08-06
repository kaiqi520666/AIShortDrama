import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import UploadFile

from app.services.image_processing import normalize_image
from app.services.storage import AUDIO_MAX_BYTES, IMAGE_MAX_BYTES, VIDEO_MAX_BYTES, OssStorage


MEDIA_UPLOAD_RULES = {
    "image": {
        "max_size": IMAGE_MAX_BYTES,
        "content_types": {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        },
    },
    "video": {
        "max_size": VIDEO_MAX_BYTES,
        "content_types": {
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/webm": ".webm",
        },
    },
    "audio": {
        "max_size": AUDIO_MAX_BYTES,
        "content_types": {
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mp4": ".m4a",
        },
    },
}


@dataclass(frozen=True)
class StoredMedia:
    object_key: str
    url: str
    content_type: str
    byte_size: int
    width: int | None
    height: int | None
    storage: OssStorage = field(repr=False, compare=False)


class MediaUploadService:
    def __init__(self, storage_factory=OssStorage):
        self.storage_factory = storage_factory

    async def store(
        self,
        file: UploadFile,
        media_type: str,
        prefix: str,
        *,
        rules: dict[str, dict[str, Any]] = MEDIA_UPLOAD_RULES,
    ) -> StoredMedia:
        normalized = None
        try:
            rule = rules.get(media_type)
            if not rule:
                raise ValueError("不支持的媒体类型")
            content_type = file.content_type or ""
            content_types = rule["content_types"]
            if content_type not in content_types:
                label = {"image": "图片", "video": "视频", "audio": "音频"}[media_type]
                raise ValueError(f"不支持的{label}格式")
            if not file.size:
                raise ValueError("上传文件不能为空")
            if file.size > rule["max_size"]:
                raise ValueError(f"文件不能超过 {self._format_size(rule['max_size'])}")

            await file.seek(0)
            upload_stream = file.file
            byte_size = file.size
            width = height = None
            if media_type == "image":
                normalized = await asyncio.to_thread(normalize_image, file.file, content_type)
                if normalized.size > rule["max_size"]:
                    raise ValueError(
                        f"重编码后的图片不能超过 {self._format_size(rule['max_size'])}"
                    )
                upload_stream = normalized.stream
                byte_size = normalized.size
                width, height = normalized.width, normalized.height
            date_path = datetime.now(UTC).strftime("%Y/%m/%d")
            object_key = f"{prefix.strip('/')}/{date_path}/{uuid.uuid4().hex}{content_types[content_type]}"
            storage = self.storage_factory()
            url = await storage.store_upload(object_key, upload_stream, content_type)
            return StoredMedia(object_key, url, content_type, byte_size, width, height, storage)
        finally:
            if normalized:
                normalized.stream.close()
            await file.close()

    @staticmethod
    async def delete(stored: StoredMedia) -> None:
        await stored.storage.delete_object(stored.object_key)

    @staticmethod
    def _format_size(value: int) -> str:
        return f"{value // (1024 * 1024)}MB" if value >= 1024 * 1024 else f"{value}B"
