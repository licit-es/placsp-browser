"""Integration tests for PgFailedEntryRepository."""

from datetime import UTC, datetime

import asyncpg
import pytest
import pytest_asyncio

from etl.repositories.failed_entry_repo import PgFailedEntryRepository

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

_NOW = datetime.now(UTC)


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(DATABASE_URL)
    yield p
    await p.execute("TRUNCATE etl_failed_entries CASCADE")
    await p.close()


@pytest.fixture
def repo(pool) -> PgFailedEntryRepository:
    return PgFailedEntryRepository(pool)


class TestRecordFailure:
    @pytest.mark.asyncio
    async def test_inserts_new_failure(
        self, repo: PgFailedEntryRepository, pool
    ) -> None:
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "parse_error",
            "Bad XML",
        )
        row = await pool.fetchrow(
            "SELECT * FROM etl_failed_entries WHERE entry_id = $1",
            "test://entry1",
        )
        assert row is not None
        assert row["feed_type"] == "outsiders"
        assert row["error_type"] == "parse_error"
        assert row["error_message"] == "Bad XML"
        assert row["retry_count"] == 1
        assert row["resolved_at"] is None

    @pytest.mark.asyncio
    async def test_upsert_increments_retry(
        self, repo: PgFailedEntryRepository, pool
    ) -> None:
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "persist_error",
            "DB timeout",
        )
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "persist_error",
            "DB timeout again",
        )
        row = await pool.fetchrow(
            "SELECT retry_count, error_message"
            " FROM etl_failed_entries"
            " WHERE entry_id = $1",
            "test://entry1",
        )
        assert row["retry_count"] == 2
        assert row["error_message"] == "DB timeout again"

    @pytest.mark.asyncio
    async def test_updates_last_failed_at(
        self, repo: PgFailedEntryRepository, pool
    ) -> None:
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "parse_error",
            "First",
        )
        row1 = await pool.fetchrow(
            "SELECT last_failed_at FROM etl_failed_entries WHERE entry_id = $1",
            "test://entry1",
        )
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "parse_error",
            "Second",
        )
        row2 = await pool.fetchrow(
            "SELECT last_failed_at FROM etl_failed_entries WHERE entry_id = $1",
            "test://entry1",
        )
        assert row2["last_failed_at"] >= row1["last_failed_at"]


class TestMarkResolved:
    @pytest.mark.asyncio
    async def test_sets_resolved_at(self, repo: PgFailedEntryRepository, pool) -> None:
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "persist_error",
            "DB error",
        )
        await repo.mark_resolved("outsiders", "test://entry1")
        row = await pool.fetchrow(
            "SELECT resolved_at FROM etl_failed_entries WHERE entry_id = $1",
            "test://entry1",
        )
        assert row["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolved_allows_new_failure(
        self, repo: PgFailedEntryRepository, pool
    ) -> None:
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "persist_error",
            "First failure",
        )
        await repo.mark_resolved("outsiders", "test://entry1")
        await repo.record_failure(
            "outsiders",
            "test://entry1",
            _NOW,
            "https://example.com/page1",
            "persist_error",
            "New failure",
        )
        count = await pool.fetchval(
            "SELECT count(*) FROM etl_failed_entries WHERE entry_id = $1",
            "test://entry1",
        )
        assert count == 2
