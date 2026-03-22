"""Orchestrator: combine similarity search with aggregate statistics.

This is the public entry point for the intelligence layer.
Route code calls ``compute_intelligence()`` and gets back everything
it needs to build the API response.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg

from api.inteligencia.estadisticas import (
    CompetitionStats,
    FrequentWinner,
    PricingStats,
    competition,
    desierta_rate,
    frequent_winners,
    pricing,
)
from api.inteligencia.similitud import (
    ScoredCandidate,
    find_candidates,
    get_ref,
)


@dataclass(frozen=True)
class IntelligenceResult:
    """Everything the route needs to build the response."""

    candidates: list[ScoredCandidate]
    pricing: PricingStats | None
    competition: CompetitionStats | None
    frequent_winners: list[FrequentWinner]
    tasa_desierta: float | None
    pool_size: int
    budget_factor: int


async def compute_intelligence(
    conn: asyncpg.Connection,
    licitacion_id: UUID,
) -> IntelligenceResult | None:
    """Find similar tenders and compute competitive intelligence.

    Returns None only if the reference tender does not exist.
    """
    ref = await get_ref(conn, licitacion_id)
    if not ref:
        return None

    candidates, budget_factor = await find_candidates(conn, ref, licitacion_id)

    if not candidates:
        return IntelligenceResult(
            candidates=[],
            pricing=None,
            competition=None,
            frequent_winners=[],
            tasa_desierta=None,
            pool_size=0,
            budget_factor=budget_factor,
        )

    pool_ids = [c.id for c in candidates]

    p = await pricing(conn, pool_ids)
    c = await competition(conn, pool_ids)
    w = await frequent_winners(conn, pool_ids)
    d = await desierta_rate(conn, pool_ids)

    return IntelligenceResult(
        candidates=candidates,
        pricing=p,
        competition=c,
        frequent_winners=w,
        tasa_desierta=d,
        pool_size=len(candidates),
        budget_factor=budget_factor,
    )
