"""FastAPI dependency injection for database access."""

from __future__ import annotations

from collections.abc import AsyncIterator

import asyncpg
from fastapi import Request


async def get_pool(request: Request) -> asyncpg.Pool:
    """Return the application-wide connection pool."""
    pool: asyncpg.Pool = request.app.state.pool  # type: ignore[assignment]
    return pool


async def get_conn(request: Request) -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the pool, release on exit."""
    pool: asyncpg.Pool = request.app.state.pool  # type: ignore[assignment]
    async with pool.acquire() as conn:
        yield conn
