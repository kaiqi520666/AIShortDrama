import base64
import binascii
import uuid
from datetime import UTC, datetime

from app.core.database import SessionLocal
from app.models import GenerationTask
from app.providers.volcengine_audio import VolcengineAudioError, VolcengineAudioProvider
from app.services.storage import OssStorage
from app.workers.generation import complete_task, update_task


AUDIO_MIME_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg_opus": "audio/ogg",
}


async def generate_audio(_ctx, task_id: str):
    await run_audio_generation(task_id)


async def run_audio_generation(
    task_id: str,
    provider: VolcengineAudioProvider | None = None,
    storage: OssStorage | None = None,
):
    task_uuid = uuid.UUID(task_id)
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_uuid)
        if not task or task.status in {"succeeded", "cancelled"}:
            return
        payload = task.request_snapshot
        task.status = "running"
        task.progress = 5
        task.started_at = datetime.now(UTC)
        await db.commit()

    owns_provider = provider is None
    try:
        provider = provider or VolcengineAudioProvider()
        storage = storage or OssStorage()
        response = await provider.synthesize(payload)
        audio_format = payload["audio_config"]["format"]
        await update_task(task_uuid, progress=90)
        if response.get("url"):
            urls = await storage.store_remote_audios(task_id, [response["url"]], audio_format)
        elif response.get("audio"):
            try:
                audio_bytes = base64.b64decode(response["audio"], validate=True)
            except (ValueError, binascii.Error) as exc:
                raise VolcengineAudioError("火山音频数据无效") from exc
            urls = [await storage.store_audio_bytes(task_id, audio_bytes, audio_format)]
        else:
            raise VolcengineAudioError("火山音频接口未返回音频地址或数据")
        duration = response.get("duration")
        await complete_task(
            task_uuid,
            "audio",
            urls,
            duration=float(duration) if isinstance(duration, (int, float)) else None,
            mime_type=AUDIO_MIME_TYPES[audio_format],
        )
    except Exception as exc:
        await update_task(
            task_uuid,
            status="failed",
            error_message=str(exc)[:2000],
            finished_at=datetime.now(UTC),
        )
        raise
    finally:
        if owns_provider and provider:
            await provider.client.aclose()
