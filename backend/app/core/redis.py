from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings


async def create_redis_pool() -> ArqRedis:
    settings = get_settings()
    return await create_pool(
        RedisSettings.from_dsn(settings.redis_url),
        default_queue_name=settings.redis_queue_name,
    )
