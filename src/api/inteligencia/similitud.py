"""Similarity algorithm: find comparable tenders by multi-dimensional scoring.

Hard filters (type_code + budget log-band) define the universe.
Soft scoring (procedure, CPV, NUTS, authority type, SARA) ranks within it.
Budget band widens adaptively (x3 -> x5 -> x10) when the pool is too small.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import asyncpg

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RefDimensions:
    """Dimensions extracted from the reference tender."""

    type_code: str | None
    procedure_code: str | None
    budget: float | None
    nuts_code: str | None
    over_threshold: bool | None
    auth_type: str | None
    cpv_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoredCandidate:
    """Candidate tender with its similarity score."""

    id: UUID
    similitud: int


# ---------------------------------------------------------------------------
# Reference-tender extraction
# ---------------------------------------------------------------------------

_REF_SQL = """
SELECT cfs.type_code,
       cfs.procedure_code,
       cfs.tax_exclusive_amount,
       cfs.nuts_code,
       cfs.over_threshold_indicator,
       cp.contracting_party_type_code
FROM contract_folder_status cfs
LEFT JOIN contracting_party cp ON cp.id = cfs.contracting_party_id
WHERE cfs.id = $1
"""

_CPV_SQL = (
    "SELECT item_classification_code"
    " FROM cpv_classification"
    " WHERE contract_folder_status_id = $1"
)


async def get_ref(
    conn: asyncpg.Connection,
    lid: UUID,
) -> RefDimensions | None:
    """Extract similarity dimensions from a tender."""
    row = await conn.fetchrow(_REF_SQL, lid)
    if not row:
        return None
    cpv_rows = await conn.fetch(_CPV_SQL, lid)
    budget = float(row["tax_exclusive_amount"]) if row["tax_exclusive_amount"] else None
    return RefDimensions(
        type_code=row["type_code"],
        procedure_code=row["procedure_code"],
        budget=budget,
        nuts_code=row["nuts_code"],
        over_threshold=row["over_threshold_indicator"],
        auth_type=row["contracting_party_type_code"],
        cpv_codes=[r["item_classification_code"] for r in cpv_rows],
    )


# ---------------------------------------------------------------------------
# Prefix lengths for hierarchical matching
# ---------------------------------------------------------------------------

# CPV hierarchy: division(2) > group(3) > class(4) > category(5) > sub(6+)
_CPV_CATEGORY = 5  # tight match: same product category
_CPV_GROUP = 3  # loose match: same service family

# NUTS hierarchy: country(2) > CCAA(4) > province(5)
_NUTS_CCAA = 4  # same autonomous community
_NUTS_COUNTRY = 2  # same country

# ---------------------------------------------------------------------------
# Candidate query builder
# ---------------------------------------------------------------------------


def _build_query(
    ref: RefDimensions,
    ref_id: UUID,
    budget_factor: int,
) -> tuple[str, list[object]]:
    """Return (sql, params) for the candidate search."""
    params: list[object] = [ref_id]
    conditions = ["cfs.id != $1"]
    idx = 2

    # -- Hard filters --------------------------------------------------

    if ref.type_code:
        conditions.append(f"cfs.type_code = ${idx}")
        params.append(ref.type_code)
        idx += 1

    if ref.budget and ref.budget > 0:
        lo = ref.budget / budget_factor
        hi = ref.budget * budget_factor
        conditions.append(f"cfs.tax_exclusive_amount BETWEEN ${idx} AND ${idx + 1}")
        params.extend([lo, hi])
        idx += 2

    # -- Soft scoring --------------------------------------------------

    score_parts: list[str] = []

    # Procedure match (+2)
    if ref.procedure_code:
        score_parts.append(f"(CASE WHEN cfs.procedure_code = ${idx} THEN 2 ELSE 0 END)")
        params.append(ref.procedure_code)
        idx += 1

    # CPV overlap: +3 for category prefix, +1 for group only
    if ref.cpv_codes:
        cat_prefixes = list(
            {c[:_CPV_CATEGORY] for c in ref.cpv_codes if len(c) >= _CPV_CATEGORY}
        )
        grp_prefixes = list(
            {c[:_CPV_GROUP] for c in ref.cpv_codes if len(c) >= _CPV_GROUP}
        )
        if cat_prefixes:
            score_parts.append(
                f"(CASE"
                f" WHEN EXISTS ("
                f"  SELECT 1 FROM cpv_classification cc"
                f"  WHERE cc.contract_folder_status_id = cfs.id"
                f"  AND left(cc.item_classification_code,"
                f" {_CPV_CATEGORY}) = ANY(${idx})"
                f" ) THEN 3"
                f" WHEN EXISTS ("
                f"  SELECT 1 FROM cpv_classification cc"
                f"  WHERE cc.contract_folder_status_id = cfs.id"
                f"  AND left(cc.item_classification_code,"
                f" {_CPV_GROUP}) = ANY(${idx + 1})"
                f" ) THEN 1"
                f" ELSE 0 END)"
            )
            params.extend([cat_prefixes, grp_prefixes])
            idx += 2

    # NUTS proximity: +2 same CCAA, +1 same country
    if ref.nuts_code and len(ref.nuts_code) >= _NUTS_CCAA:
        score_parts.append(
            f"(CASE"
            f" WHEN left(cfs.nuts_code, {_NUTS_CCAA}) = ${idx} THEN 2"
            f" WHEN left(cfs.nuts_code, {_NUTS_COUNTRY}) = ${idx + 1} THEN 1"
            f" ELSE 0 END)"
        )
        params.extend([ref.nuts_code[:_NUTS_CCAA], ref.nuts_code[:_NUTS_COUNTRY]])
        idx += 2
    elif ref.nuts_code and len(ref.nuts_code) >= _NUTS_COUNTRY:
        score_parts.append(
            f"(CASE WHEN left(cfs.nuts_code, {_NUTS_COUNTRY}) = ${idx}"
            f" THEN 1 ELSE 0 END)"
        )
        params.append(ref.nuts_code[:_NUTS_COUNTRY])
        idx += 1

    # Authority type match (+1)
    if ref.auth_type:
        score_parts.append(
            f"(CASE WHEN cp.contracting_party_type_code = ${idx} THEN 1 ELSE 0 END)"
        )
        params.append(ref.auth_type)
        idx += 1

    # SARA threshold match (+1)
    if ref.over_threshold is not None:
        score_parts.append(
            f"(CASE WHEN cfs.over_threshold_indicator"
            f" IS NOT DISTINCT FROM ${idx}"
            f" THEN 1 ELSE 0 END)"
        )
        params.append(ref.over_threshold)
        idx += 1

    score_expr = " + ".join(score_parts) if score_parts else "0"
    where = " AND ".join(conditions)

    sql = f"""
        SELECT cfs.id, ({score_expr}) AS similitud
        FROM contract_folder_status cfs
        LEFT JOIN contracting_party cp
          ON cp.id = cfs.contracting_party_id
        WHERE {where}
        ORDER BY similitud DESC, cfs.updated DESC
        LIMIT 200
    """
    return sql, params


# ---------------------------------------------------------------------------
# Adaptive search
# ---------------------------------------------------------------------------

_MIN_POOL = 10


async def find_candidates(
    conn: asyncpg.Connection,
    ref: RefDimensions,
    ref_id: UUID,
) -> tuple[list[ScoredCandidate], int]:
    """Find candidates, widening budget band if pool is too small.

    Returns (candidates, budget_factor_used).
    """
    rows: list[asyncpg.Record] = []
    for factor in (3, 5, 10):
        sql, params = _build_query(ref, ref_id, factor)
        rows = await conn.fetch(sql, *params)
        if len(rows) >= _MIN_POOL:
            return (
                [ScoredCandidate(id=r["id"], similitud=r["similitud"]) for r in rows],
                factor,
            )
    # Return whatever we got at widest factor
    return (
        [ScoredCandidate(id=r["id"], similitud=r["similitud"]) for r in rows],
        10,
    )
