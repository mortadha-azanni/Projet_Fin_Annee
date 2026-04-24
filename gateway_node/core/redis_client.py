import redis.asyncio as redis
from core.config import settings

_redis_client: redis.Redis | None = None

async def create_redis() -> redis.Redis:
    """Create the global async Redis connection pool."""
    global _redis_client
    _redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,  # DB 0 for gateway pubsub/cache, avoiding DB 1 used by Celery
        decode_responses=True
    )
    return _redis_client

async def close_redis() -> None:
    """Close the global async Redis connection pool."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None

def get_redis() -> redis.Redis:
    """Get the active Redis connection pool."""
    if _redis_client is None:
        raise RuntimeError("Redis pool is not initialized")
    return _redis_client
