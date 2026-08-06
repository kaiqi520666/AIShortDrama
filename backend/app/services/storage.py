import asyncio
from io import BytesIO
import tempfile
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx
import oss2

from app.core.config import get_settings

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}
AUDIO_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
}
IMAGE_MAX_BYTES = 20 * 1024 * 1024
VIDEO_MAX_BYTES = 500 * 1024 * 1024
AUDIO_MAX_BYTES = 100 * 1024 * 1024


class MediaSizeLimitError(RuntimeError):
    pass


class OssStorage:
    def __init__(self):
        settings = get_settings()
        required = {
            "OSS_ACCESS_KEY_ID": settings.oss_access_key_id,
            "OSS_ACCESS_KEY_SECRET": settings.oss_access_key_secret,
            "OSS_ENDPOINT": settings.oss_endpoint,
            "OSS_BUCKET_NAME": settings.oss_bucket_name,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"OSS 配置缺失：{', '.join(missing)}")
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        self.bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)
        self.public_base_url = settings.oss_public_base_url.rstrip("/")

    async def store_upload(self, object_key: str, stream, content_type: str) -> str:
        await asyncio.to_thread(
            self.bucket.put_object,
            object_key,
            stream,
            {"Content-Type": content_type},
        )
        return f"{self.public_base_url}/{object_key}"

    async def store_remote_images(self, task_id: str, urls: list[str]) -> list[str]:
        return await self._store_remote_media(
            task_id,
            urls,
            "images",
            CONTENT_TYPE_EXTENSIONS,
            ".png",
            IMAGE_MAX_BYTES,
            "图片",
        )

    async def store_remote_videos(self, task_id: str, urls: list[str]) -> list[str]:
        return await self._store_remote_media(
            task_id,
            urls,
            "videos",
            VIDEO_EXTENSIONS,
            ".mp4",
            VIDEO_MAX_BYTES,
            "视频",
        )

    async def store_remote_audios(
        self, task_id: str, urls: list[str], audio_format: str
    ) -> list[str]:
        fallback = {"mp3": ".mp3", "wav": ".wav", "ogg_opus": ".ogg"}[audio_format]
        return await self._store_remote_media(
            task_id,
            urls,
            "audios",
            AUDIO_EXTENSIONS,
            fallback,
            AUDIO_MAX_BYTES,
            "音频",
        )

    async def store_audio_bytes(self, task_id: str, data: bytes, audio_format: str) -> str:
        if len(data) > AUDIO_MAX_BYTES:
            raise MediaSizeLimitError(f"音频文件不能超过 {AUDIO_MAX_BYTES // (1024 * 1024)}MB")
        extension, content_type = {
            "mp3": (".mp3", "audio/mpeg"),
            "wav": (".wav", "audio/wav"),
            "ogg_opus": (".ogg", "audio/ogg"),
        }[audio_format]
        return await self.store_upload(
            f"generations/audios/{task_id}-1{extension}", BytesIO(data), content_type
        )

    async def _store_remote_media(
        self,
        task_id: str,
        urls: list[str],
        media_dir: str,
        content_type_extensions: dict[str, str],
        fallback_extension: str,
        max_bytes: int,
        media_label: str,
    ) -> list[str]:
        stored = []
        timeout = httpx.Timeout(300, connect=30)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for index, url in enumerate(urls, start=1):
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_length = response.headers.get("content-length")
                    if (
                        content_length
                        and content_length.isdigit()
                        and int(content_length) > max_bytes
                    ):
                        raise MediaSizeLimitError(
                            f"{media_label}文件不能超过 {max_bytes // (1024 * 1024)}MB"
                        )
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    extension = (
                        content_type_extensions.get(content_type)
                        or PurePosixPath(urlparse(url).path).suffix.lower()
                    )
                    allowed_extensions = set(content_type_extensions.values())
                    extension = extension if extension in allowed_extensions else fallback_extension
                    extension_types = {value: key for key, value in content_type_extensions.items()}
                    content_type = (
                        content_type
                        if content_type in content_type_extensions
                        else extension_types[extension]
                    )
                    object_key = f"generations/{media_dir}/{task_id}-{index}{extension}"
                    headers = {"Content-Type": content_type}
                    with tempfile.TemporaryFile() as stream:
                        downloaded = 0
                        async for chunk in response.aiter_bytes():
                            downloaded += len(chunk)
                            if downloaded > max_bytes:
                                raise MediaSizeLimitError(
                                    f"{media_label}文件不能超过 {max_bytes // (1024 * 1024)}MB"
                                )
                            stream.write(chunk)
                        stream.seek(0)
                        await asyncio.to_thread(self.bucket.put_object, object_key, stream, headers)
                stored.append(f"{self.public_base_url}/{object_key}")
        return stored
