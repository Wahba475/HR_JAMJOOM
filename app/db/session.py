"""Async DB connection pool — plain asyncpg, no ORM."""

import asyncio

import asyncpg

from app.config import DATABASE_URL

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """Lazily create the pool once, reuse it after.

    The lock matters: score_cv fans out per CV, so on the first run many
    branches reach this at the same moment. Without it each one sees
    _pool is None and builds its own pool, opening dozens of connections
    at once — Neon stops accepting them and every branch but the first
    hangs. Re-checked inside the lock so only one pool is ever built.
    """
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=20)
    return _pool
