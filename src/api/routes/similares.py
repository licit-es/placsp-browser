"""GET /similares/{id} — similar tenders with competitive intelligence."""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_conn
from api.inteligencia.estadisticas import confidence
from api.inteligencia.similares import IntelligenceResult, compute_intelligence
from api.schemas import DISPLAY_COLS
from api.schemas.similares import (
    AdjudicatarioFrecuente,
    EstadisticasCompetencia,
    EstadisticasPrecio,
    EstadisticasSimilares,
    LicitacionSimilar,
    RespuestaSimilares,
)

router = APIRouter(tags=["Similares"])


@router.get(
    "/similares/{licitacion_id}",
    response_model=RespuestaSimilares,
    summary="Licitaciones similares con inteligencia competitiva",
)
async def get_similares(
    licitacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    estado: str | None = Query(None, description="Filtrar por estado"),
    limit: int = Query(10, ge=1, le=50),
) -> RespuestaSimilares:
    """Find structurally similar tenders and return market intelligence."""
    intel = await compute_intelligence(conn, licitacion_id)
    if intel is None:
        raise HTTPException(status_code=404, detail="Licitacion no encontrada")

    if not intel.candidates:
        return _empty_response(intel.budget_factor)

    # Pick top N candidates by similitud for display.
    display_candidates = intel.candidates[:limit]
    display_ids = [c.id for c in display_candidates]
    score_map = {c.id: c.similitud for c in display_candidates}

    # Fetch display fields from the presentation view.
    params: list[object] = [display_ids]
    where_extra = ""
    if estado:
        where_extra = " AND v.estado ILIKE $2"
        params.append(f"%{estado}%")

    rows = await conn.fetch(
        f"""
        SELECT {DISPLAY_COLS}
        FROM v_licitacion v
        WHERE v.id = ANY($1) {where_extra}
        """,
        *params,
    )

    resultados = sorted(
        [
            LicitacionSimilar.from_row(r, similitud=score_map.get(r["id"], 0))
            for r in rows
        ],
        key=lambda x: (-x.similitud, x.fecha_actualizacion),
        reverse=False,
    )

    # Build estadisticas from intelligence result.
    pricing_schema = None
    if intel.pricing:
        pricing_schema = EstadisticasPrecio(
            n=intel.pricing.n,
            p25=intel.pricing.p25,
            mediana=intel.pricing.mediana,
            p75=intel.pricing.p75,
        )

    competition_schema = None
    if intel.competition:
        competition_schema = EstadisticasCompetencia(
            media=intel.competition.media,
            mediana=intel.competition.mediana,
        )

    return RespuestaSimilares(
        resultados=resultados,
        estadisticas=EstadisticasSimilares(
            n=intel.pool_size,
            baja_pct=pricing_schema,
            num_licitadores=competition_schema,
            adjudicatarios_frecuentes=[
                AdjudicatarioFrecuente(
                    nombre=w.nombre,
                    n=w.n,
                    baja_media_pct=w.baja_media_pct,
                )
                for w in intel.frequent_winners
            ],
            tasa_desierta=intel.tasa_desierta,
            nivel_confianza=_confidence_label(intel),
            factor_presupuesto=intel.budget_factor,
        ),
    )


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _confidence_label(intel: IntelligenceResult) -> str:
    """Map pricing sample size to a human label."""
    return confidence(intel.pricing)


def _empty_response(budget_factor: int) -> RespuestaSimilares:
    return RespuestaSimilares(
        resultados=[],
        estadisticas=EstadisticasSimilares(
            n=0,
            baja_pct=None,
            num_licitadores=None,
            adjudicatarios_frecuentes=[],
            tasa_desierta=None,
            nivel_confianza="baja",
            factor_presupuesto=budget_factor,
        ),
    )
