"""Landing page statistics from the mv_landing_stats materialized view."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import asyncpg


@dataclass(frozen=True)
class LandingStats:
    """Aggregate numbers shown on the landing page."""

    total_licitaciones: int
    total_organos: int
    total_empresas: int
    importe_total: Decimal
    ultima_actualizacion: datetime | None


async def fetch_landing_stats(
    conn: asyncpg.Connection,
) -> LandingStats:
    """Read pre-computed stats from the materialized view."""
    row = await conn.fetchrow("SELECT * FROM mv_landing_stats")
    if row is None:
        return LandingStats(
            total_licitaciones=0,
            total_organos=0,
            total_empresas=0,
            importe_total=Decimal(0),
            ultima_actualizacion=None,
        )
    return LandingStats(
        total_licitaciones=row["total_licitaciones"],
        total_organos=row["total_organos"],
        total_empresas=row["total_empresas"],
        importe_total=row["importe_total"],
        ultima_actualizacion=row["ultima_actualizacion"],
    )
