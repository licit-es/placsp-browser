"""SyncStateRepository — tracks ETL pagination state."""

from __future__ import annotations

import uuid

import asyncpg

from shared.models.etl import EtlSyncStateRead


class PgSyncStateRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_or_create(
        self,
        feed_type: str,
        year: int,
        page_url: str,
    ) -> EtlSyncStateRead:
        row = await self._pool.fetchrow(
            'INSERT INTO etl_sync_state'
            " (feed_type, year, page_url, status)"
            " VALUES ($1, $2, $3, 'pending')"
            " ON CONFLICT (feed_type, year, page_url) DO NOTHING"
            " RETURNING *",
            feed_type,
            year,
            page_url,
        )
        if row is None:
            row = await self._pool.fetchrow(
                'SELECT * FROM etl_sync_state'
                " WHERE feed_type = $1"
                " AND year = $2"
                " AND page_url = $3",
                feed_type,
                year,
                page_url,
            )
        return EtlSyncStateRead(**dict(row))

    async def update_status(
        self,
        sync_id: uuid.UUID,
        status: str,
        entry_count: int,
        error_count: int,
    ) -> None:
        await self._pool.execute(
            'UPDATE etl_sync_state'
            " SET status = $2,"
            " entry_count = $3,"
            " error_count = $4,"
            " processed_at = now()"
            " WHERE id = $1",
            sync_id,
            status,
            entry_count,
            error_count,
        )

    async def find_resume_point(
        self,
        feed_type: str,
        year: int,
    ) -> str | None:
        row = await self._pool.fetchrow(
            'SELECT page_url FROM etl_sync_state'
            " WHERE feed_type = $1"
            " AND year = $2"
            " AND status IN ('in_progress', 'failed')"
            " ORDER BY page_url"
            " LIMIT 1",
            feed_type,
            year,
        )
        if row is None:
            return None
        return str(row["page_url"])
