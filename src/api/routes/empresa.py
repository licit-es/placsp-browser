"""Empresa endpoints — search and profile."""

from __future__ import annotations

from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from api.auth import get_current_user
from api.deps import get_conn
from api.render import MARKDOWN_RESPONSES, negotiate
from api.renderers.markdown import render_empresa_md, render_empresas_md
from api.schemas import (
    DISPLAY_COLS,
    LICITACION_VIEW,
    EmpresaDetalle,
    EmpresaResumen,
    EmpresaStats,
    LicitacionResumen,
    PeticionBusquedaEmpresas,
    decode_cursor,
    encode_cursor,
)

router = APIRouter(tags=["Empresas"])


@router.post(
    "/empresas",
    response_model=list[EmpresaResumen],
    responses=MARKDOWN_RESPONSES,
    summary="Buscar empresas adjudicatarias",
)
async def buscar_empresas(
    request: Request,
    body: PeticionBusquedaEmpresas,
    conn: asyncpg.Connection = Depends(get_conn),
    _user: asyncpg.Record = Depends(get_current_user),
) -> Response:
    """Search companies by name, NIF or city."""
    rows = await conn.fetch(
        """
        SELECT e.nif, e.nombre,
          (SELECT count(DISTINCT tr.contract_folder_status_id)
           FROM winning_party wp
           JOIN tender_result tr ON tr.id = wp.tender_result_id
           WHERE wp.identifier = e.nif) AS contratos
        FROM empresa e
        WHERE e.nombre % $1
           OR e.nif ILIKE '%' || $1 || '%'
        ORDER BY similarity(e.nombre, $1) DESC, contratos DESC
        LIMIT $2
        """,
        body.q,
        body.limite,
    )
    data = [
        EmpresaResumen(
            id=r["nif"],
            nombre=r["nombre"],
            contratos=r["contratos"],
        )
        for r in rows
    ]
    return negotiate(request, data, render_empresas_md)


@router.get(
    "/empresa/{empresa_id}",
    response_model=EmpresaDetalle,
    responses=MARKDOWN_RESPONSES,
    summary="Perfil de empresa adjudicataria",
)
async def get_empresa(
    request: Request,
    empresa_id: str,
    conn: asyncpg.Connection = Depends(get_conn),
    _user: asyncpg.Record = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Resultados por pagina."),
    cursor: str | None = Query(None, description="Cursor de paginacion."),
) -> Response:
    """Company profile with aggregated stats and paginated adjudications."""
    stats_row = await conn.fetchrow(
        """
        SELECT
          e.nombre,
          count(DISTINCT va.licitacion_id) AS contratos,
          sum(va.importe_adjudicacion) AS importe_total,
          avg(va.importe_adjudicacion)
            FILTER (WHERE va.importe_adjudicacion > 0) AS importe_medio,
          avg(
            CASE WHEN va.presupuesto_sin_iva > 0
              THEN (1 - va.importe_adjudicacion
                      / va.presupuesto_sin_iva) * 100
            END
          ) FILTER (WHERE va.importe_adjudicacion > 0
                    AND va.presupuesto_sin_iva > 0) AS baja_media
        FROM empresa e
        JOIN v_adjudicacion va ON va.adjudicatario_nif = e.nif
        WHERE e.nif = $1
        GROUP BY e.nombre
        """,
        empresa_id,
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
        empresa_id,
    )

    organo_rows = await conn.fetch(
        """
        SELECT organo, count(*) AS n
        FROM v_adjudicacion
        WHERE adjudicatario_nif = $1
        GROUP BY organo ORDER BY n DESC LIMIT 5
        """,
        empresa_id,
    )

    # Paginated adjudications
    cursor_cond = ""
    params: list[object] = [empresa_id, limit + 1]
    if cursor:
        sort_val, cursor_id = decode_cursor(cursor)
        cursor_cond = " AND (v.fecha_actualizacion, v.id) < ($3::timestamptz, $4::uuid)"
        params.extend([datetime.fromisoformat(sort_val), cursor_id])

    rows = await conn.fetch(
        f"""
        SELECT {DISPLAY_COLS}
        FROM {LICITACION_VIEW} v
        WHERE v.adjudicatario_nif = $1 {cursor_cond}
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

    data = EmpresaDetalle(
        id=empresa_id,
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
        adjudicaciones=[LicitacionResumen.from_row(r) for r in rows],
        cursor_siguiente=cursor_siguiente,
    )
    return negotiate(request, data, render_empresa_md)
