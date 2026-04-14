import asyncpg
from .config import settings

async def get_db():
    """Dependency that yields a database connection."""
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        ssl=settings.DB_SSL
    )
    try:
        yield conn
    finally:
        await conn.close()
