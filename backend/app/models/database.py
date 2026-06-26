import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20,
        )
        if settings.db_schema:
            async with _pool.acquire() as conn:
                await conn.execute(f"SET search_path TO {settings.db_schema}, public")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
