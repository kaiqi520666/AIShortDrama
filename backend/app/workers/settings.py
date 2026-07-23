from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.image_generation import generate_image
from app.workers.audio_generation import generate_audio
from app.workers.video_generation import generate_video

settings = get_settings()


class WorkerSettings:
    functions = [generate_image, generate_video, generate_audio]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    queue_name = settings.redis_queue_name
    job_timeout = 1500
    max_tries = 1
