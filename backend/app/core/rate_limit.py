import hashlib


FIXED_WINDOW_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if redis.call('TTL', KEYS[1]) < 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def hashed_identifier(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def increment_fixed_window(redis, key: str, window_seconds: int) -> int:
    return int(await redis.eval(FIXED_WINDOW_SCRIPT, 1, key, window_seconds))
