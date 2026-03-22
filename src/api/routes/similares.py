"""GET /similares/{id} — similar tenders with competitive intelligence."""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_conn
from api.inteligencia.estadisticas import confidence
from api.inteligencia.similares import IntelligenceResult, compute_intelligence
from api.schemas.similares import (
    AdjudicatarioFrecuente,
    EstadisticasCompetencia,
    EstadisticasPrecio,
    EstadisticasSimilares,
    LicitacionSimilar,
    RespuestaSimilares,
)

router = APIRouter(tags=["Similares"])

# Display fields from v_licitacion (shared with buscar/organo).
_DISPLAY_COLS = """
    v.id, v.expediente, v.titulo, v.organo,
    v.tipo_contrato, v.estado, v.presupuesto_sin_iva,
    v.importe_adjudicacion, v.fecha_publicacion,
    v.fecha_actualizacion, v.fecha_adjudicacion,
    v.cpv_principal, v.num_licitadores, v.adjudicatario,
    v.lugar_subentidad AS lugar,
    v.tiene_documentos, v.num_lotes,
    v.historial_estados
"""


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
        SELECT {_DISPLAY_COLS}
        FROM v_licitacion v
        WHERE v.id = ANY($1) {where_extra}
        """,
        *params,
    )

    resultados = sorted(
        [_row_to_similar(r, score_map) for r in rows],
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


def _row_to_similar(
    r: asyncpg.Record,
    score_map: dict[UUID, int],
) -> LicitacionSimilar:
    return LicitacionSimilar(
        id=r["id"],
        expediente=r["expediente"],
        titulo=r["titulo"],
        organo=r["organo"],
        tipo_contrato=r["tipo_contrato"],
        estado=r["estado"],
        presupuesto_sin_iva=r["presupuesto_sin_iva"],
        importe_adjudicacion=r["importe_adjudicacion"],
        fecha_publicacion=r["fecha_publicacion"],
        fecha_actualizacion=r["fecha_actualizacion"],
        fecha_adjudicacion=r["fecha_adjudicacion"],
        cpv_principal=r["cpv_principal"],
        num_licitadores=r["num_licitadores"],
        adjudicatario=r["adjudicatario"],
        lugar=r["lugar"],
        tiene_documentos=r["tiene_documentos"],
        num_lotes=r["num_lotes"],
        historial_estados=r["historial_estados"] or [],
        similitud=score_map.get(r["id"], 0),
    )


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
