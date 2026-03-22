"""FailedEntryRepository — logs and resolves entry processing failures."""

from __future__ import annotations

from datetime import datetime

import asyncpg


class PgFailedEntryRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record_failure(
        self,
        feed_type: str,
        entry_id: str,
        entry_updated: datetime | None,
        page_url: str,
        error_type: str,
        error_message: str,
    ) -> None:
        await self._pool.execute(
            'INSERT INTO etl_failed_entries'
            " (feed_type, entry_id, entry_updated,"
            "  page_url, error_type, error_message)"
            " VALUES ($1, $2, $3, $4, $5, $6)"
            " ON CONFLICT (feed_type, entry_id)"
            " WHERE resolved_at IS NULL"
            " DO UPDATE SET"
            '  retry_count = etl_failed_entries.retry_count + 1,'
            "  last_failed_at = now(),"
            "  error_message = EXCLUDED.error_message",
            feed_type,
            entry_id,
            entry_updated,
            page_url,
            error_type,
            error_message,
        )

    async def mark_resolved(
        self,
        feed_type: str,
        entry_id: str,
    ) -> None:
        await self._pool.execute(
            'UPDATE etl_failed_entries'
            " SET resolved_at = now()"
            " WHERE feed_type = $1"
            " AND entry_id = $2"
            " AND resolved_at IS NULL",
            feed_type,
            entry_id,
        )
