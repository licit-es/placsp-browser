"""Database connection pool management."""
from __future__ import annotations

import asyncpg

from shared.config import Settings


async def create_pool(settings: Settings | None = None) -> asyncpg.Pool:
    """Create an asyncpg connection pool."""
    settings = settings or Settings()
    pool = await asyncpg.create_pool(settings.database_url)
    if pool is None:
        msg = "Failed to create connection pool"
        raise RuntimeError(msg)
    return pool
