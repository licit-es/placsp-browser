"""GET /empresa/{nif} — company profile from adjudication history."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_conn
from api.schemas import EmpresaDetalle, EmpresaStats, LicitacionResumen

router = APIRouter(tags=["Empresas"])


@router.get(
    "/empresa/{nif}",
    response_model=EmpresaDetalle,
    summary="Perfil de empresa adjudicataria",
)
async def get_empresa(
    nif: str,
    conn: asyncpg.Connection = Depends(get_conn),  # type: ignore[assignment]
) -> EmpresaDetalle:
    """Company profile with aggregated stats and recent adjudications."""
    stats_row = await conn.fetchrow(
        """
        SELECT
          adjudicatario AS nombre,
          count(DISTINCT licitacion_id) AS contratos,
          sum(importe_adjudicacion) AS importe_total,
          avg(importe_adjudicacion)
            FILTER (WHERE importe_adjudicacion > 0) AS importe_medio,
          avg(
            CASE WHEN presupuesto_sin_iva > 0
              THEN (1 - importe_adjudicacion / presupuesto_sin_iva) * 100
            END
          ) FILTER (WHERE importe_adjudicacion > 0
                    AND presupuesto_sin_iva > 0) AS baja_media
        FROM v_adjudicacion
        WHERE adjudicatario_nif = $1
        GROUP BY adjudicatario
        ORDER BY contratos DESC LIMIT 1
        """,
        nif,
    )
    if not stats_row:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    cpv_rows = await conn.fetch(
        """
        SELECT vc.codigo, count(*) AS n
        FROM v_adjudicacion va
        JOIN v_cpv vc ON vc.licitacion_id = va.licitacion_id AND vc.lote_id IS NULL
        WHERE va.adjudicatario_nif = $1
        GROUP BY vc.codigo ORDER BY n DESC LIMIT 5
        """,
        nif,
    )

    organo_rows = await conn.fetch(
        """
        SELECT organo, count(*) AS n
        FROM v_adjudicacion
        WHERE adjudicatario_nif = $1
        GROUP BY organo ORDER BY n DESC LIMIT 5
        """,
        nif,
    )

    recientes = await conn.fetch(
        """
        SELECT v.id, v.expediente, v.titulo, v.organo,
               v.tipo_contrato, v.estado, v.presupuesto_sin_iva,
               v.importe_adjudicacion, v.fecha_publicacion,
               v.fecha_adjudicacion, v.cpv_principal,
               v.num_licitadores, v.adjudicatario,
               v.lugar_subentidad AS lugar,
               v.tiene_documentos, v.num_lotes
        FROM v_licitacion v
        WHERE v.adjudicatario_nif = $1
        ORDER BY v.fecha_publicacion DESC LIMIT 20
        """,
        nif,
    )

    return EmpresaDetalle(
        nif=nif,
        nombre=stats_row["nombre"],
        stats=EmpresaStats(
            contratos_adjudicados=stats_row["contratos"],
            importe_total=stats_row["importe_total"],
            importe_medio=stats_row["importe_medio"],
            cpv_frecuentes=[r["codigo"] for r in cpv_rows],
            organos_frecuentes=[r["organo"] for r in organo_rows],
            baja_media_pct=(
                round(stats_row["baja_media"], 2)
                if stats_row["baja_media"] is not None
                else None
            ),
        ),
        adjudicaciones_recientes=[
            LicitacionResumen(
                id=r["id"],
                expediente=r["expediente"],
                titulo=r["titulo"],
                organo=r["organo"],
                tipo_contrato=r["tipo_contrato"],
                estado=r["estado"],
                presupuesto_sin_iva=r["presupuesto_sin_iva"],
                importe_adjudicacion=r["importe_adjudicacion"],
                fecha_publicacion=r["fecha_publicacion"],
                fecha_adjudicacion=r["fecha_adjudicacion"],
                cpv_principal=r["cpv_principal"],
                num_licitadores=r["num_licitadores"],
                adjudicatario=r["adjudicatario"],
                lugar=r["lugar"],
                tiene_documentos=r["tiene_documentos"],
                num_lotes=r["num_lotes"],
            )
            for r in recientes
        ],
    )
