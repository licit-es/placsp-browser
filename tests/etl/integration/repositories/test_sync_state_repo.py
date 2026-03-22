"""Integration tests for PgSyncStateRepository."""

import asyncpg
import pytest
import pytest_asyncio

from etl.repositories.sync_state_repo import PgSyncStateRepository

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(DATABASE_URL)
    yield p
    await p.execute('TRUNCATE "EtlSyncState" CASCADE')
    await p.close()


@pytest.fixture
def repo(pool) -> PgSyncStateRepository:
    return PgSyncStateRepository(pool)


class TestGetOrCreate:
    @pytest.mark.asyncio
    async def test_creates_new_state(self, repo: PgSyncStateRepository) -> None:
        state = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        assert state.feed_type == "outsiders"
        assert state.year == 0
        assert state.page_url == "https://example.com/page1"
        assert state.status == "pending"
        assert state.id is not None

    @pytest.mark.asyncio
    async def test_returns_existing(self, repo: PgSyncStateRepository) -> None:
        s1 = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        s2 = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        assert s1.id == s2.id

    @pytest.mark.asyncio
    async def test_different_pages_distinct(self, repo: PgSyncStateRepository) -> None:
        s1 = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        s2 = await repo.get_or_create("outsiders", 0, "https://example.com/page2")
        assert s1.id != s2.id


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_updates_status_and_counts(
        self, repo: PgSyncStateRepository, pool
    ) -> None:
        state = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        await repo.update_status(state.id, "completed", entry_count=10, error_count=1)
        row = await pool.fetchrow(
            'SELECT * FROM "EtlSyncState" WHERE id = $1',
            state.id,
        )
        assert row["status"] == "completed"
        assert row["entry_count"] == 10
        assert row["error_count"] == 1
        assert row["processed_at"] is not None


class TestFindResumePoint:
    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, repo: PgSyncStateRepository) -> None:
        result = await repo.find_resume_point("outsiders", 0)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_all_completed(
        self, repo: PgSyncStateRepository
    ) -> None:
        state = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        await repo.update_status(state.id, "completed", entry_count=5, error_count=0)
        result = await repo.find_resume_point("outsiders", 0)
        assert result is None

    @pytest.mark.asyncio
    async def test_finds_in_progress_page(self, repo: PgSyncStateRepository) -> None:
        state = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        await repo.update_status(state.id, "in_progress", entry_count=0, error_count=0)
        result = await repo.find_resume_point("outsiders", 0)
        assert result == "https://example.com/page1"

    @pytest.mark.asyncio
    async def test_finds_failed_page(self, repo: PgSyncStateRepository) -> None:
        state = await repo.get_or_create("outsiders", 0, "https://example.com/page1")
        await repo.update_status(state.id, "failed", entry_count=3, error_count=2)
        result = await repo.find_resume_point("outsiders", 0)
        assert result == "https://example.com/page1"
