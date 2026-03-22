"""GET /organo/{id} — contracting body profile."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_conn
from api.schemas import LicitacionResumen, OrganoDetalle, OrganoStats

router = APIRouter(tags=["Organos"])


@router.get(
    "/organo/{organo_id}",
    response_model=OrganoDetalle,
    summary="Perfil de organo de contratacion",
)
async def get_organo(
    organo_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),  # type: ignore[assignment]  # noqa: B008
) -> OrganoDetalle:
    """Contracting body profile with stats and recent tenders."""
    org = await conn.fetchrow(
        "SELECT id, name, nif, contracting_party_type_code"
        " FROM contracting_party WHERE id = $1",
        organo_id,
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organo no encontrado")

    # Stats
    stats_row = await conn.fetchrow(
        """
        SELECT
          count(*) AS total,
          avg(tax_exclusive_amount)
            FILTER (WHERE tax_exclusive_amount > 0) AS importe_medio,
          avg(
            EXTRACT(DAY FROM (
              tr.award_date::timestamp - cfs.updated
            ))
          ) FILTER (WHERE tr.award_date IS NOT NULL) AS plazo_medio
        FROM contract_folder_status cfs
        LEFT JOIN LATERAL (
          SELECT award_date FROM tender_result t
          WHERE t.contract_folder_status_id = cfs.id
          ORDER BY t.award_date DESC NULLS LAST LIMIT 1
        ) tr ON true
        WHERE cfs.contracting_party_id = $1
        """,
        organo_id,
    )

    # Top CPVs
    cpv_rows = await conn.fetch(
        """
        SELECT cc.item_classification_code, count(*) AS n
        FROM contract_folder_status cfs
        JOIN cpv_classification cc ON cc.contract_folder_status_id = cfs.id
          AND cc.lot_id IS NULL
        WHERE cfs.contracting_party_id = $1
        GROUP BY cc.item_classification_code
        ORDER BY n DESC LIMIT 5
        """,
        organo_id,
    )

    # Recent tenders
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
        WHERE v.organo_id = $1
        ORDER BY v.fecha_publicacion DESC
        LIMIT 20
        """,
        organo_id,
    )

    plazo = stats_row["plazo_medio"] if stats_row else None

    return OrganoDetalle(
        id=org["id"],
        nombre=org["name"],
        nif=org["nif"],
        tipo=org["contracting_party_type_code"],
        stats=OrganoStats(
            total_licitaciones=stats_row["total"] if stats_row else 0,
            importe_medio=stats_row["importe_medio"] if stats_row else None,
            cpv_frecuentes=[r["item_classification_code"] for r in cpv_rows],
            plazo_medio_adjudicacion_dias=(
                round(plazo) if plazo is not None else None
            ),
        ),
        licitaciones_recientes=[
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
