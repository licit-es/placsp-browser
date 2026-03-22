"""Aggregate statistics from a pool of comparable tenders.

All functions receive a list of candidate IDs (already selected by
similitud.find_candidates) and compute market intelligence from them.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PricingStats:
    """Baja-% distribution from resolved comparables."""

    n: int
    p25: float
    mediana: float
    p75: float


@dataclass(frozen=True)
class CompetitionStats:
    """Bidder-count distribution."""

    media: float
    mediana: float


@dataclass(frozen=True)
class FrequentWinner:
    """A frequent winner in the comparable pool."""

    nombre: str
    n: int
    baja_media_pct: float | None


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_MIN_PRICING = 3
_CONFIDENCE_MEDIA = 10
_CONFIDENCE_ALTA = 30

_PRICING_SQL = """
SELECT count(*) AS n,
       percentile_cont(ARRAY[0.25, 0.5, 0.75])
         WITHIN GROUP (ORDER BY baja) AS pcts
FROM (
  SELECT
    (1.0 - tr.awarded_tax_exclusive_amount
         / COALESCE(NULLIF(l.tax_exclusive_amount, 0),
                    cfs.tax_exclusive_amount)
    ) AS baja
  FROM tender_result tr
  JOIN contract_folder_status cfs
    ON cfs.id = tr.contract_folder_status_id
  LEFT JOIN procurement_project_lot l
    ON l.id = tr.lot_id
  WHERE cfs.id = ANY($1)
    AND tr.awarded_tax_exclusive_amount > 0
    AND COALESCE(NULLIF(l.tax_exclusive_amount, 0),
                 cfs.tax_exclusive_amount) > 0
    AND tr.awarded_tax_exclusive_amount
      / COALESCE(NULLIF(l.tax_exclusive_amount, 0),
                 cfs.tax_exclusive_amount)
      BETWEEN 0.3 AND 1.2
) sub
"""

_COMPETITION_SQL = """
SELECT avg(sub.licitadores)::float AS media,
       percentile_cont(0.5)
         WITHIN GROUP (ORDER BY sub.licitadores::float) AS mediana
FROM (
  SELECT DISTINCT ON (tr.contract_folder_status_id)
         tr.received_tender_quantity AS licitadores
  FROM tender_result tr
  WHERE tr.contract_folder_status_id = ANY($1)
    AND tr.received_tender_quantity IS NOT NULL
    AND tr.received_tender_quantity > 0
  ORDER BY tr.contract_folder_status_id,
           tr.award_date DESC NULLS LAST
) sub
"""

_WINNERS_SQL = """
SELECT va.adjudicatario AS nombre,
       count(*)          AS n,
       avg(
         CASE WHEN va.presupuesto_sin_iva > 0
               AND va.importe_adjudicacion > 0
         THEN (1.0 - va.importe_adjudicacion
                    / va.presupuesto_sin_iva) * 100
         END
       ) AS baja_media_pct
FROM v_adjudicacion va
WHERE va.licitacion_id = ANY($1)
  AND va.adjudicatario IS NOT NULL
GROUP BY va.adjudicatario
ORDER BY count(*) DESC
LIMIT 5
"""

_DESIERTA_SQL = """
SELECT count(*) FILTER (
         WHERE EXISTS (
           SELECT 1 FROM tender_result tr
           WHERE tr.contract_folder_status_id = cfs.id
             AND tr.result_code IN ('5', '8')
         )
       ) AS desiertas,
       count(*) AS total
FROM contract_folder_status cfs
WHERE cfs.id = ANY($1)
  AND cfs.status_code NOT IN ('PUB', 'EV', 'BORR', 'PRE')
"""

# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


async def pricing(
    conn: asyncpg.Connection,
    ids: list[UUID],
) -> PricingStats | None:
    """Compute baja-% percentiles from resolved candidates."""
    row = await conn.fetchrow(_PRICING_SQL, ids)
    if not row or row["n"] < _MIN_PRICING:
        return None
    pcts = row["pcts"]
    return PricingStats(
        n=row["n"],
        p25=round(float(pcts[0]) * 100, 1),
        mediana=round(float(pcts[1]) * 100, 1),
        p75=round(float(pcts[2]) * 100, 1),
    )


async def competition(
    conn: asyncpg.Connection,
    ids: list[UUID],
) -> CompetitionStats | None:
    """Compute bidder-count distribution (deduplicated per tender)."""
    row = await conn.fetchrow(_COMPETITION_SQL, ids)
    if not row or row["media"] is None:
        return None
    return CompetitionStats(
        media=round(float(row["media"]), 1),
        mediana=round(float(row["mediana"]), 1),
    )


async def frequent_winners(
    conn: asyncpg.Connection,
    ids: list[UUID],
) -> list[FrequentWinner]:
    """Top 5 most frequent winners in the candidate pool."""
    rows = await conn.fetch(_WINNERS_SQL, ids)
    return [
        FrequentWinner(
            nombre=r["nombre"],
            n=r["n"],
            baja_media_pct=(
                round(float(r["baja_media_pct"]), 1)
                if r["baja_media_pct"] is not None
                else None
            ),
        )
        for r in rows
    ]


async def desierta_rate(
    conn: asyncpg.Connection,
    ids: list[UUID],
) -> float | None:
    """Proportion of terminal-state tenders that went desierta."""
    row = await conn.fetchrow(_DESIERTA_SQL, ids)
    if not row or not row["total"]:
        return None
    return round(row["desiertas"] / row["total"], 3)


def confidence(pricing_stats: PricingStats | None) -> str:
    """Map pricing sample size to a confidence label."""
    if pricing_stats is None or pricing_stats.n < _MIN_PRICING:
        return "baja"
    if pricing_stats.n < _CONFIDENCE_MEDIA:
        return "baja"
    if pricing_stats.n < _CONFIDENCE_ALTA:
        return "media"
    return "alta"
