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
    conn: asyncpg.Connection = Depends(get_conn),  # type: ignore[assignment]  # noqa: B008
) -> EmpresaDetalle:
    """Company profile with aggregated stats and recent adjudications."""
    # Find company name + basic stats
    stats_row = await conn.fetchrow(
        """
        SELECT
          wp.name,
          count(DISTINCT tr.contract_folder_status_id) AS contratos,
          sum(tr.awarded_tax_exclusive_amount) AS importe_total,
          avg(tr.awarded_tax_exclusive_amount)
            FILTER (WHERE tr.awarded_tax_exclusive_amount > 0) AS importe_medio,
          avg(
            CASE WHEN cfs.tax_exclusive_amount > 0
              THEN (1 - tr.awarded_tax_exclusive_amount
                      / cfs.tax_exclusive_amount) * 100
            END
          ) FILTER (WHERE tr.awarded_tax_exclusive_amount > 0
                    AND cfs.tax_exclusive_amount > 0) AS baja_media
        FROM winning_party wp
        JOIN tender_result tr ON tr.id = wp.tender_result_id
        JOIN contract_folder_status cfs ON cfs.id = tr.contract_folder_status_id
        WHERE wp.identifier = $1
        GROUP BY wp.name
        ORDER BY contratos DESC
        LIMIT 1
        """,
        nif,
    )
    if not stats_row:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    nombre = stats_row["name"]

    # Top CPVs
    cpv_rows = await conn.fetch(
        """
        SELECT cc.item_classification_code, count(*) AS n
        FROM winning_party wp
        JOIN tender_result tr ON tr.id = wp.tender_result_id
        JOIN cpv_classification cc ON cc.contract_folder_status_id
             = tr.contract_folder_status_id
        WHERE wp.identifier = $1 AND cc.lot_id IS NULL
        GROUP BY cc.item_classification_code
        ORDER BY n DESC LIMIT 5
        """,
        nif,
    )

    # Top organos
    organo_rows = await conn.fetch(
        """
        SELECT cp.name, count(*) AS n
        FROM winning_party wp
        JOIN tender_result tr ON tr.id = wp.tender_result_id
        JOIN contract_folder_status cfs ON cfs.id = tr.contract_folder_status_id
        JOIN contracting_party cp ON cp.id = cfs.contracting_party_id
        WHERE wp.identifier = $1
        GROUP BY cp.name
        ORDER BY n DESC LIMIT 5
        """,
        nif,
    )

    # Recent adjudications
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
        WHERE EXISTS (
          SELECT 1 FROM tender_result tr
          JOIN winning_party wp ON wp.tender_result_id = tr.id
          WHERE tr.contract_folder_status_id = v.id
            AND wp.identifier = $1
        )
        ORDER BY v.fecha_publicacion DESC
        LIMIT 20
        """,
        nif,
    )

    return EmpresaDetalle(
        nif=nif,
        nombre=nombre,
        stats=EmpresaStats(
            contratos_adjudicados=stats_row["contratos"],
            importe_total=stats_row["importe_total"],
            importe_medio=stats_row["importe_medio"],
            cpv_frecuentes=[r["item_classification_code"] for r in cpv_rows],
            organos_frecuentes=[r["name"] for r in organo_rows],
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
