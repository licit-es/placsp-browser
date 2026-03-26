"""Organo endpoints — search and profile."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_conn
from api.schemas import (
    DISPLAY_COLS,
    LicitacionResumen,
    OrganoDetalle,
    OrganoResumen,
    OrganoStats,
    PeticionBusquedaOrganos,
    decode_cursor,
    encode_cursor,
)

router = APIRouter(tags=["Organos"])


@router.post(
    "/organos",
    response_model=list[OrganoResumen],
    summary="Buscar organos de contratacion",
)
async def buscar_organos(
    body: PeticionBusquedaOrganos,
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[OrganoResumen]:
    """Search contracting bodies by name, NIF or DIR3."""
    rows = await conn.fetch(
        """
        SELECT cp.id, cp.name, cp.nif,
          (SELECT count(*)
           FROM contract_folder_status cfs
           WHERE cfs.contracting_party_id = cp.id) AS licitaciones
        FROM contracting_party cp
        WHERE cp.name % $1
           OR cp.nif ILIKE '%' || $1 || '%'
           OR cp.dir3 ILIKE '%' || $1 || '%'
        ORDER BY similarity(cp.name, $1) DESC, licitaciones DESC
        LIMIT $2
        """,
        body.q,
        body.limite,
    )
    return [
        OrganoResumen(
            id=r["id"],
            nombre=r["name"],
            nif=r["nif"],
            licitaciones=r["licitaciones"],
        )
        for r in rows
    ]


@router.get(
    "/organo/{organo_id}",
    response_model=OrganoDetalle,
    summary="Perfil de organo de contratacion",
)
async def get_organo(
    organo_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    limit: int = Query(20, ge=1, le=100, description="Resultados por pagina."),
    cursor: str | None = Query(None, description="Cursor de paginacion."),
) -> OrganoDetalle:
    """Contracting body profile with stats and paginated tenders."""
    # Use v_licitacion for a single row to get resolved organo fields
    org = await conn.fetchrow(
        "SELECT organo_id, organo, organo_nif, organo_tipo"
        " FROM v_licitacion WHERE organo_id = $1 LIMIT 1",
        organo_id,
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organo no encontrado")

    stats_row = await conn.fetchrow(
        """
        SELECT
          count(*) AS total,
          avg(presupuesto_sin_iva)
            FILTER (WHERE presupuesto_sin_iva > 0) AS importe_medio,
          avg(EXTRACT(DAY FROM (
            fecha_adjudicacion::timestamp - fecha_limite::timestamp
          ))) FILTER (WHERE fecha_adjudicacion IS NOT NULL
                      AND fecha_limite IS NOT NULL
                      AND fecha_adjudicacion > fecha_limite) AS plazo_medio
        FROM v_licitacion
        WHERE organo_id = $1
        """,
        organo_id,
    )

    cpv_rows = await conn.fetch(
        """
        SELECT vc.codigo, count(*) AS n
        FROM v_licitacion v
        JOIN v_cpv vc ON vc.licitacion_id = v.id AND vc.lote_id IS NULL
        WHERE v.organo_id = $1
        GROUP BY vc.codigo ORDER BY n DESC LIMIT 5
        """,
        organo_id,
    )

    # Paginated licitaciones
    cursor_cond = ""
    params: list[object] = [organo_id, limit + 1]
    if cursor:
        sort_val, cursor_id = decode_cursor(cursor)
        cursor_cond = " AND (v.fecha_actualizacion, v.id) < ($3::timestamptz, $4::uuid)"
        params.extend([datetime.fromisoformat(sort_val), cursor_id])

    rows = await conn.fetch(
        f"""
        SELECT {DISPLAY_COLS}
        FROM v_licitacion v
        WHERE v.organo_id = $1 {cursor_cond}
        ORDER BY v.fecha_actualizacion DESC, v.id DESC
        LIMIT $2
        """,
        *params,
    )
    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    cursor_siguiente = None
    if has_next and rows:
        last = rows[-1]
        cursor_siguiente = encode_cursor(last["fecha_actualizacion"], last["id"])

    plazo = stats_row["plazo_medio"] if stats_row else None

    return OrganoDetalle(
        id=org["organo_id"],
        nombre=org["organo"],
        nif=org["organo_nif"],
        tipo=org["organo_tipo"],
        stats=OrganoStats(
            total_licitaciones=stats_row["total"] if stats_row else 0,
            importe_medio=stats_row["importe_medio"] if stats_row else None,
            cpv_frecuentes=[r["codigo"] for r in cpv_rows],
            plazo_medio_adjudicacion_dias=(round(plazo) if plazo is not None else None),
        ),
        licitaciones=[LicitacionResumen.from_row(r) for r in rows],
        cursor_siguiente=cursor_siguiente,
    )
