from typing import AsyncGenerator

import asyncpg  # type: ignore[import-untyped]
from .config import settings

# Pool is stored on the module so main.py can reference it in lifespan
_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    """Create the global connection pool. Called once at startup."""
    global _pool
    _pool = await asyncpg.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        ssl=settings.db_ssl_effective,
        min_size=2,
        max_size=10,
    )
    return _pool


async def close_pool() -> None:
    """Close the pool gracefully. Called once at shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency — acquires a connection from the pool."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    async with _pool.acquire() as conn:
        yield conn
