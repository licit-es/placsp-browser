"""Integration tests for PgCatalogRepository."""

import os

import asyncpg
import pytest
import pytest_asyncio

from etl.repositories.catalog_repo import PgCatalogRepository

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)

_TABLES = [
    "cat_status_code",
    "cat_type_code",
    "cat_procedure_code",
    "cat_urgency_code",
    "cat_result_code",
    "cat_contracting_system",
    "cat_nuts",
    "cat_cpv",
]


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(DATABASE_URL)
    for t in _TABLES:
        await p.execute(f"DELETE FROM {t}")
    yield p
    for t in _TABLES:
        await p.execute(f"DELETE FROM {t}")
    await p.close()


@pytest.fixture
def repo(pool) -> PgCatalogRepository:
    return PgCatalogRepository(pool)


class TestGetPendingCodes:
    @pytest.mark.asyncio
    async def test_returns_inactive_codes(
        self, repo: PgCatalogRepository, pool
    ) -> None:
        await pool.execute("INSERT INTO cat_cpv (code) VALUES ('30200000')")
        codes = await repo.get_pending_codes("cat_cpv")
        assert "30200000" in codes

    @pytest.mark.asyncio
    async def test_excludes_active_codes(self, repo: PgCatalogRepository, pool) -> None:
        await pool.execute(
            "INSERT INTO cat_cpv (code, active) VALUES ('30200000', true)"
        )
        codes = await repo.get_pending_codes("cat_cpv")
        assert "30200000" not in codes


class TestActivateCodes:
    @pytest.mark.asyncio
    async def test_inserts_and_activates(self, repo: PgCatalogRepository, pool) -> None:
        count = await repo.activate_codes(
            "cat_cpv",
            {"30200000": "Computer equipment"},
        )
        assert count == 1
        row = await pool.fetchrow("SELECT * FROM cat_cpv WHERE code = '30200000'")
        assert row["active"] is True
        assert row["description"] == "Computer equipment"

    @pytest.mark.asyncio
    async def test_updates_existing_inactive(
        self, repo: PgCatalogRepository, pool
    ) -> None:
        await pool.execute("INSERT INTO cat_cpv (code) VALUES ('30200000')")
        count = await repo.activate_codes(
            "cat_cpv",
            {"30200000": "Updated description"},
        )
        assert count == 1
        row = await pool.fetchrow("SELECT * FROM cat_cpv WHERE code = '30200000'")
        assert row["active"] is True
        assert row["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_returns_affected_count(self, repo: PgCatalogRepository) -> None:
        count = await repo.activate_codes(
            "cat_nuts",
            {"ES300": "Madrid", "ES511": "Barcelona"},
        )
        assert count == 2


class TestEnsureCode:
    @pytest.mark.asyncio
    async def test_inserts_new_code(self, repo: PgCatalogRepository, pool) -> None:
        await repo.ensure_code("cat_cpv", "44000000")
        row = await pool.fetchrow("SELECT * FROM cat_cpv WHERE code = '44000000'")
        assert row is not None
        assert row["active"] is False

    @pytest.mark.asyncio
    async def test_idempotent(self, repo: PgCatalogRepository, pool) -> None:
        await repo.ensure_code("cat_cpv", "44000000")
        await repo.ensure_code("cat_cpv", "44000000")
        count = await pool.fetchval(
            "SELECT count(*) FROM cat_cpv WHERE code = '44000000'"
        )
        assert count == 1


class TestAllCatalogTables:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("table", _TABLES)
    async def test_ensure_code_works(
        self, repo: PgCatalogRepository, table: str
    ) -> None:
        await repo.ensure_code(table, "TEST001")
        codes = await repo.get_pending_codes(table)
        assert "TEST001" in codes


class TestInvalidTable:
    @pytest.mark.asyncio
    async def test_rejects_invalid_table(self, repo: PgCatalogRepository) -> None:
        with pytest.raises(ValueError, match="Invalid catalog"):
            await repo.get_pending_codes("not_a_table")
