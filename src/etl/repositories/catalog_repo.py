"""CatalogRepository — manages genericode catalog tables."""

from __future__ import annotations

import asyncpg

_VALID_TABLES = frozenset(
    {
        "cat_status_code",
        "cat_type_code",
        "cat_procedure_code",
        "cat_urgency_code",
        "cat_result_code",
        "cat_contracting_system",
        "cat_nuts",
        "cat_cpv",
    }
)


def _validate_table(table: str) -> None:
    if table not in _VALID_TABLES:
        msg = f"Invalid catalog table: {table}"
        raise ValueError(msg)


class PgCatalogRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_pending_codes(self, table: str) -> list[str]:
        _validate_table(table)
        rows = await self._pool.fetch(
            f"SELECT code FROM {table} WHERE active = false ORDER BY code",
        )
        return [r["code"] for r in rows]

    async def activate_codes(
        self,
        table: str,
        codes: dict[str, str],
    ) -> int:
        _validate_table(table)
        count = 0
        for code, description in codes.items():
            result = await self._pool.execute(
                f"INSERT INTO {table}"
                " (code, description, active)"
                " VALUES ($1, $2, true)"
                " ON CONFLICT (code) DO UPDATE"
                " SET description = EXCLUDED.description,"
                " active = true",
                code,
                description,
            )
            # asyncpg returns "INSERT 0 1" or "UPDATE 1" etc.
            count += int(result.split()[-1])
        return count

    async def ensure_code(self, table: str, code: str) -> None:
        _validate_table(table)
        await self._pool.execute(
            f"INSERT INTO {table} (code) VALUES ($1) ON CONFLICT (code) DO NOTHING",
            code,
        )
