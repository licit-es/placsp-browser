"""In-memory catalog cache for label → code translation.

Loaded once at startup. Used by filter logic to accept human-readable
labels and translate them to CODICE codes for indexed filtering.
"""
from __future__ import annotations

import asyncpg

# Catalogs to cache (small lookup tables, NOT cpv/nuts).
_TABLES: dict[str, str] = {
    "tipo_contrato": "cat_type_code",
    "estado": "cat_status_code",
    "procedimiento": "cat_procedure_code",
    "tramitacion": "cat_urgency_code",
    "resultado": "cat_result_code",
    "sistema_contratacion": "cat_contracting_system",
    "tipo_organo": "cat_contracting_authority_type",
    "programa_financiacion": "cat_funding_program",
}

# label (casefolded) → code
_caches: dict[str, dict[str, str]] = {}


async def load(pool: asyncpg.Pool) -> None:
    """Load all small catalogs into memory."""
    async with pool.acquire() as conn:
        for name, table in _TABLES.items():
            rows = await conn.fetch(
                f"SELECT code, description FROM {table}"  # noqa: S608
            )
            cache: dict[str, str] = {}
            for r in rows:
                if r["description"]:
                    cache[r["description"].casefold()] = r["code"]
            _caches[name] = cache


def to_codes(catalog: str, labels: list[str]) -> list[str]:
    """Translate labels to codes. Unknown values pass through as-is."""
    cache = _caches.get(catalog, {})
    return [cache.get(lbl.casefold(), lbl) for lbl in labels]
