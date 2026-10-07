import base64
import binascii
import logging
import uuid

from app.core.errors import diagnostic_snapshot, public_error_message
from app.providers.protocols import AudioProvider
from app.providers.volcengine_audio import VolcengineAudioError
from app.providers.registry import create_generation_provider, adapt_generation_provider
from app.services.provider_execution import SubmissionNeedsReview, submit_provider_task
from app.services.task_lifecycle import mark_needs_review, queue_task, start_task
from app.services.storage import OssStorage
from app.workers.generation import complete_task, fail_task, update_task, run_queued_worker


logger = logging.getLogger(__name__)


AUDIO_MIME_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg_opus": "audio/ogg",
}


async def generate_audio(_ctx, task_id: str):
    await run_queued_worker(run_audio_generation, task_id)


async def run_audio_generation(
    task_id: str,
    provider: AudioProvider | None = None,
    storage: OssStorage | None = None,
):
    task_uuid = uuid.UUID(task_id)
    task = await start_task(task_uuid)
    if task is None:
        return
    token = task.worker_lease_token
    payload = task.request_snapshot

    owns_provider = provider is None
    stage = "recover" if task.submission_started_at or task.provider_response else "submit"
    try:
        provider = (
            adapt_generation_provider(provider, "audio") if provider is not None
            else create_generation_provider(task.provider, "audio")
        )
        response = await submit_provider_task(task, provider)
        audio_format = payload["audio_config"]["format"]
        if not await update_task(task_uuid, progress=90, worker_token=token):
            raise SubmissionNeedsReview("任务已暂停或交由其他 worker 处理")
        stage = "storage"
        storage = storage or OssStorage()
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
        original_duration = response.get("original_duration")
        if not isinstance(original_duration, (int, float)) or original_duration <= 0:
            raise VolcengineAudioError("火山音频接口未返回有效计费时长")
        stage = "billing"
        await complete_task(
            task_uuid,
            "audio",
            urls,
            duration=float(duration) if isinstance(duration, (int, float)) else None,
            original_duration=float(original_duration),
            mime_type=AUDIO_MIME_TYPES[audio_format],
            worker_token=token,
        )
    except SubmissionNeedsReview as exc:
        await mark_needs_review(task_uuid, str(exc), worker_token=token)
    except Exception as exc:
        logger.exception("Audio generation failed", extra={"task_id": str(task_uuid)})
        if stage == "recover":
            await queue_task(
                task_uuid, "上游结果恢复暂时失败，等待重试",
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        elif (
            stage == "submit" and task.submission_started_at
            and (getattr(exc, "retryable", False) or not isinstance(exc, VolcengineAudioError))
        ):
            await mark_needs_review(
                task_uuid, "上游提交结果未知，请人工核对后再处理",
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        elif stage in {"storage", "billing"}:
            await queue_task(
                task_uuid, "生成结果处理失败，等待重试", diagnostic_snapshot(exc, stage), worker_token=token,
            )
        else:
            await fail_task(
                task_uuid, "failed", public_error_message(exc, "音频生成服务暂时不可用"),
                diagnostic_snapshot(exc, stage), worker_token=token,
            )
        raise
    finally:
        if owns_provider and provider:
            await provider.aclose()
