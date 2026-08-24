from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.credits import replenish_daily_credits
from app.workers.image_generation import generate_image
from app.workers.audio_generation import generate_audio
from app.workers.video_generation import generate_video
from app.workers.generation import compensate_stale_generation_tasks

settings = get_settings()


class WorkerSettings:
    functions = [generate_image, generate_video, generate_audio]
    cron_jobs = [
        cron(compensate_stale_generation_tasks, minute={0, 10, 20, 30, 40, 50}),
        # ARQ uses UTC; 16:00 UTC is 00:00 in Asia/Shanghai.
        cron(replenish_daily_credits, hour=16, minute=0, run_at_startup=True),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    queue_name = settings.redis_queue_name
    job_timeout = 1500
    max_tries = 1
