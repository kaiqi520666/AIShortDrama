import asyncio
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
        stored = []
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            for index, url in enumerate(urls, start=1):
                response = await client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                extension = (
                    CONTENT_TYPE_EXTENSIONS.get(content_type)
                    or PurePosixPath(urlparse(url).path).suffix
                )
                extension = extension if extension in {".jpg", ".jpeg", ".png", ".webp"} else ".png"
                object_key = f"generations/images/{task_id}-{index}{extension}"
                headers = {"Content-Type": content_type} if content_type else None
                await asyncio.to_thread(
                    self.bucket.put_object,
                    object_key,
                    response.content,
                    headers,
                )
                stored.append(f"{self.public_base_url}/{object_key}")
        return stored

    async def store_remote_videos(self, task_id: str, urls: list[str]) -> list[str]:
        stored = []
        timeout = httpx.Timeout(300, connect=30)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for index, url in enumerate(urls, start=1):
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    extension = (
                        VIDEO_EXTENSIONS.get(content_type)
                        or PurePosixPath(urlparse(url).path).suffix.lower()
                    )
                    extension = extension if extension in {".mp4", ".mov", ".webm"} else ".mp4"
                    content_type = content_type if content_type in VIDEO_EXTENSIONS else {
                        ".mp4": "video/mp4",
                        ".mov": "video/quicktime",
                        ".webm": "video/webm",
                    }[extension]
                    object_key = f"generations/videos/{task_id}-{index}{extension}"
                    headers = {"Content-Type": content_type}
                    with tempfile.TemporaryFile() as stream:
                        async for chunk in response.aiter_bytes():
                            stream.write(chunk)
                        stream.seek(0)
                        await asyncio.to_thread(self.bucket.put_object, object_key, stream, headers)
                stored.append(f"{self.public_base_url}/{object_key}")
        return stored
