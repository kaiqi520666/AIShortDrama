import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, File, UploadFile

from app.schemas.response import fail, success
from app.services.storage import OssStorage

router = APIRouter()

UPLOAD_RULES = {
    "image": {
        "max_size": 20 * 1024 * 1024,
        "content_types": {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        },
    },
    "video": {
        "max_size": 500 * 1024 * 1024,
        "content_types": {
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/webm": ".webm",
        },
    },
}


@router.post("/{media_type}")
async def upload_media(media_type: str, file: UploadFile = File(...)):
    rule = UPLOAD_RULES.get(media_type)
    if not rule:
        return fail("不支持的媒体类型")
    if file.content_type not in rule["content_types"]:
        return fail(f"不支持的{('图片' if media_type == 'image' else '视频')}格式")
    if not file.size:
        return fail("上传文件不能为空")
    if file.size > rule["max_size"]:
        limit = (
            f"{rule['max_size'] // (1024 * 1024)}MB"
            if rule["max_size"] >= 1024 * 1024
            else f"{rule['max_size']}B"
        )
        return fail(f"文件不能超过 {limit}")

    extension = rule["content_types"][file.content_type]
    date_path = datetime.now(UTC).strftime("%Y/%m/%d")
    object_key = f"uploads/{media_type}s/{date_path}/{uuid.uuid4().hex}{extension}"
    try:
        await file.seek(0)
        url = await OssStorage().store_upload(object_key, file.file, file.content_type)
    except Exception as exc:
        return fail(f"上传失败：{exc}")
    finally:
        await file.close()

    return success(
        {
            "url": url,
            "object_key": object_key,
            "content_type": file.content_type,
            "size": file.size,
        }
    )
