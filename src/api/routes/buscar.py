# ruff: noqa: S608
"""POST /buscar — unified search endpoint."""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends

from api.deps import get_conn
from api.schemas import (
    FiltrosBusqueda,
    LicitacionResumen,
    PeticionBusqueda,
    RespuestaBusqueda,
    decode_cursor,
    encode_cursor,
)

router = APIRouter(tags=["Buscar"])

_SORT_MAP = {
    "fecha": "v.fecha_publicacion DESC, v.id DESC",
    "importe": "v.presupuesto_sin_iva DESC NULLS LAST, v.id DESC",
    "relevancia": "rank DESC, v.id DESC",
}


def _apply_filters(
    f: FiltrosBusqueda,
    conditions: list[str],
    params: list[object],
    idx: int,
) -> int:
    """Append filter conditions and params. Returns next param index."""
    if f.tipo_contrato:
        conditions.append(f"v.tipo_contrato = ANY(${idx})")
        params.append(f.tipo_contrato)
        idx += 1
    if f.estado:
        conditions.append(f"v.estado = ANY(${idx})")
        params.append(f.estado)
        idx += 1
    if f.cpv_prefijo:
        conditions.append(
            f"EXISTS (SELECT 1 FROM cpv_classification cc"
            f" WHERE cc.contract_folder_status_id = v.id"
            f" AND cc.item_classification_code LIKE ${idx})"
        )
        params.append(f"{f.cpv_prefijo}%")
        idx += 1
    if f.importe_min is not None:
        conditions.append(f"v.presupuesto_sin_iva >= ${idx}")
        params.append(f.importe_min)
        idx += 1
    if f.importe_max is not None:
        conditions.append(f"v.presupuesto_sin_iva <= ${idx}")
        params.append(f.importe_max)
        idx += 1
    if f.fecha_publicacion_desde:
        conditions.append(f"v.fecha_publicacion >= ${idx}")
        params.append(f.fecha_publicacion_desde)
        idx += 1
    if f.fecha_publicacion_hasta:
        conditions.append(f"v.fecha_publicacion <= ${idx}")
        params.append(f.fecha_publicacion_hasta)
        idx += 1
    if f.procedimiento:
        conditions.append(f"v.procedimiento = ANY(${idx})")
        params.append(f.procedimiento)
        idx += 1
    if f.ccaa:
        conditions.append(f"v.lugar_subentidad ILIKE ${idx}")
        params.append(f"%{f.ccaa}%")
        idx += 1
    if f.adjudicatario:
        conditions.append(
            f"EXISTS (SELECT 1 FROM tender_result tr"
            f" JOIN winning_party wp ON wp.tender_result_id = tr.id"
            f" WHERE tr.contract_folder_status_id = v.id"
            f" AND wp.name ILIKE ${idx})"
        )
        params.append(f"%{f.adjudicatario}%")
        idx += 1
    if f.organo:
        conditions.append(f"v.organo ILIKE ${idx}")
        params.append(f"%{f.organo}%")
        idx += 1
    if f.financiacion_ue is not None:
        op = "IS NOT NULL" if f.financiacion_ue else "IS NULL"
        conditions.append(f"v.funding_program_code {op}")
    return idx


def _apply_cursor(
    body: PeticionBusqueda,
    conditions: list[str],
    params: list[object],
    idx: int,
) -> int:
    """Append cursor-based keyset pagination conditions."""
    if not body.cursor:
        return idx
    sort_val, cursor_id = decode_cursor(body.cursor)
    sort_key = body.ordenar

    if sort_key == "fecha" or (sort_key == "relevancia" and not body.q):
        conditions.append(
            f"(v.fecha_publicacion, v.id)"
            f" < (${idx}::timestamptz, ${idx + 1}::uuid)"
        )
        params.extend([sort_val, cursor_id])
        idx += 2
    elif sort_key == "importe":
        conditions.append(
            f"(COALESCE(v.presupuesto_sin_iva, 0), v.id)"
            f" < (${idx}::decimal, ${idx + 1}::uuid)"
        )
        params.extend([sort_val, cursor_id])
        idx += 2
    elif sort_key == "relevancia" and body.q:
        conditions.append(
            f"(ts_rank(v.search_vector,"
            f" plainto_tsquery('spanish', ${idx})), v.id)"
            f" < (${idx + 1}::real, ${idx + 2}::uuid)"
        )
        params.append(body.q)
        params.extend([sort_val, cursor_id])
        idx += 3
    return idx


def _row_to_resumen(r: asyncpg.Record) -> LicitacionResumen:
    return LicitacionResumen(
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
        relevancia=round(float(r["rank"]), 4) if r["rank"] else None,
    )


@router.post(
    "/buscar",
    response_model=RespuestaBusqueda,
    summary="Busqueda unificada de licitaciones",
)
async def buscar(
    body: PeticionBusqueda,
    conn: asyncpg.Connection = Depends(get_conn),  # type: ignore[assignment]  # noqa: B008
) -> RespuestaBusqueda:
    """Unified search: free text + structured filters, cursor pagination."""
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if body.q:
        conditions.append(
            f"v.search_vector @@ plainto_tsquery('spanish', ${idx})"
        )
        params.append(body.q)
        idx += 1

    if body.filtros:
        idx = _apply_filters(body.filtros, conditions, params, idx)
    idx = _apply_cursor(body, conditions, params, idx)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Sort
    sort_key = body.ordenar
    if sort_key == "relevancia" and not body.q:
        sort_key = "fecha"
    order_sql = _SORT_MAP[sort_key]

    rank_expr = "0 AS rank"
    if body.q:
        rank_expr = (
            "ts_rank(v.search_vector, plainto_tsquery('spanish', $1)) AS rank"
        )

    total = await conn.fetchval(
        f"SELECT count(*) FROM v_licitacion v {where}",
        *params,
    )

    fetch_limit = body.limit + 1
    data_sql = f"""
        SELECT v.id, v.expediente, v.titulo, v.organo,
               v.tipo_contrato, v.estado, v.presupuesto_sin_iva,
               v.importe_adjudicacion, v.fecha_publicacion,
               v.fecha_adjudicacion, v.cpv_principal,
               v.num_licitadores, v.adjudicatario,
               v.lugar_subentidad AS lugar,
               v.tiene_documentos, v.num_lotes,
               {rank_expr}
        FROM v_licitacion v
        {where}
        ORDER BY {order_sql}
        LIMIT ${idx}
    """
    params.append(fetch_limit)

    rows = await conn.fetch(data_sql, *params)
    has_next = len(rows) > body.limit
    if has_next:
        rows = rows[: body.limit]

    resultados = [_row_to_resumen(r) for r in rows]

    cursor_siguiente = None
    if has_next and rows:
        last = rows[-1]
        if sort_key == "fecha":
            cursor_siguiente = encode_cursor(
                last["fecha_publicacion"], last["id"]
            )
        elif sort_key == "importe":
            cursor_siguiente = encode_cursor(
                last["presupuesto_sin_iva"] or 0, last["id"]
            )
        elif sort_key == "relevancia":
            cursor_siguiente = encode_cursor(last["rank"], last["id"])

    return RespuestaBusqueda(
        total=total or 0,
        resultados=resultados,
        cursor_siguiente=cursor_siguiente,
    )
