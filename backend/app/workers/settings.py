from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.image_generation import generate_image

settings = get_settings()


class WorkerSettings:
    functions = [generate_image]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    queue_name = settings.redis_queue_name
    job_timeout = 180
    max_tries = 1
