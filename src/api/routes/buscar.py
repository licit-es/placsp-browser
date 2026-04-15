"""POST /buscar — unified search endpoint."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import asyncpg
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from api.auth import get_current_user
from api.catalogs import to_codes
from api.deps import get_conn
from api.render import MARKDOWN_RESPONSES, negotiate
from api.renderers.markdown import render_busqueda_md
from api.schemas import (
    DISPLAY_COLS,
    LICITACION_VIEW,
    DocumentoResumen,
    FiltrosBusqueda,
    LicitacionResumen,
    PeticionBusqueda,
    RespuestaBusqueda,
    decode_cursor,
    encode_cursor,
)

router = APIRouter(tags=["Licitaciones"])

_SORT_MAP = {
    "fecha": "v.fecha_actualizacion DESC, v.id DESC",
    "importe": "v.presupuesto_sin_iva DESC NULLS LAST, v.id DESC",
    "relevancia": "rank DESC, v.id DESC",
}


def _append(
    conditions: list[str],
    params: list[object],
    idx: int,
    expr: str,
    value: object,
) -> int:
    """Append a single parameterised condition. Returns next param index."""
    conditions.append(expr.replace("$N", f"${idx}"))
    params.append(value)
    return idx + 1


def _apply_entity_filters(
    f: FiltrosBusqueda,
    conditions: list[str],
    params: list[object],
    idx: int,
) -> int:
    """Append entity/location filters. Returns next param index."""
    if f.ccaa:
        idx = _append(
            conditions,
            params,
            idx,
            "v.lugar_subentidad ILIKE $N",
            f"%{f.ccaa}%",
        )
    if f.adjudicatario:
        idx = _append(
            conditions,
            params,
            idx,
            "EXISTS (SELECT 1 FROM tender_result tr"
            " JOIN winning_party wp ON wp.tender_result_id = tr.id"
            " WHERE tr.contract_folder_status_id = v.id"
            " AND wp.name ILIKE $N)",
            f"%{f.adjudicatario}%",
        )
    if f.organo_id:
        idx = _append(
            conditions,
            params,
            idx,
            "v.organo_id = $N",
            f.organo_id,
        )
    elif f.organo:
        idx = _append(
            conditions,
            params,
            idx,
            "v.organo ILIKE $N",
            f"%{f.organo}%",
        )
    if f.financiacion_ue is not None:
        op = "IS NOT NULL" if f.financiacion_ue else "IS NULL"
        conditions.append(f"v.funding_program_code {op}")
    return idx


def _apply_filters(
    f: FiltrosBusqueda,
    conditions: list[str],
    params: list[object],
    idx: int,
) -> int:
    """Append filter conditions and params. Returns next param index."""
    if f.tipo_contrato:
        idx = _append(
            conditions,
            params,
            idx,
            "v.type_code = ANY($N)",
            to_codes("tipo_contrato", f.tipo_contrato),
        )
    if f.estado:
        idx = _append(
            conditions,
            params,
            idx,
            "v.status_code = ANY($N)",
            to_codes("estado", f.estado),
        )
    if f.cpv_prefijo:
        idx = _append(
            conditions,
            params,
            idx,
            "EXISTS (SELECT 1 FROM cpv_classification cc"
            " WHERE cc.contract_folder_status_id = v.id"
            " AND cc.item_classification_code LIKE $N)",
            f"{f.cpv_prefijo}%",
        )
    if f.importe_min is not None:
        idx = _append(
            conditions,
            params,
            idx,
            "v.presupuesto_sin_iva >= $N",
            f.importe_min,
        )
    if f.importe_max is not None:
        idx = _append(
            conditions,
            params,
            idx,
            "v.presupuesto_sin_iva <= $N",
            f.importe_max,
        )
    if f.fecha_publicacion_desde:
        idx = _append(
            conditions,
            params,
            idx,
            "v.fecha_publicacion >= $N",
            f.fecha_publicacion_desde,
        )
    if f.fecha_publicacion_hasta:
        idx = _append(
            conditions,
            params,
            idx,
            "v.fecha_publicacion <= $N",
            f.fecha_publicacion_hasta,
        )
    if f.procedimiento:
        idx = _append(
            conditions,
            params,
            idx,
            "v.procedure_code = ANY($N)",
            to_codes("procedimiento", f.procedimiento),
        )
    return _apply_entity_filters(f, conditions, params, idx)


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
            f"(v.fecha_actualizacion, v.id) < (${idx}::timestamptz, ${idx + 1}::uuid)"
        )
        params.extend([datetime.fromisoformat(sort_val), cursor_id])
        idx += 2
    elif sort_key == "importe":
        conditions.append(
            f"(COALESCE(v.presupuesto_sin_iva, 0), v.id)"
            f" < (${idx}::decimal, ${idx + 1}::uuid)"
        )
        params.extend([Decimal(sort_val), cursor_id])
        idx += 2
    elif sort_key == "relevancia" and body.q:
        conditions.append(
            f"(ts_rank(v.search_vector,"
            f" plainto_tsquery('spanish', ${idx})), v.id)"
            f" < (${idx + 1}::real, ${idx + 2}::uuid)"
        )
        params.append(body.q)
        params.extend([float(sort_val), cursor_id])
        idx += 3
    return idx


def _row_to_resumen(
    r: asyncpg.Record,
    docs: list[DocumentoResumen] | None = None,
) -> LicitacionResumen:
    return LicitacionResumen.from_row(
        r,
        documentos=docs,
        relevancia=round(float(r["rank"]), 4) if r["rank"] else None,
    )


@router.post(
    "/buscar",
    response_model=RespuestaBusqueda,
    responses=MARKDOWN_RESPONSES,
    summary="Busqueda unificada de licitaciones",
)
async def buscar(
    body: PeticionBusqueda,
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    _user: asyncpg.Record = Depends(get_current_user),
) -> Response:
    """Unified search: free text + structured filters, cursor pagination."""
    request.state.search_params = body.model_dump(exclude_none=True)
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if body.q:
        conditions.append(f"v.search_vector @@ plainto_tsquery('spanish', ${idx})")
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
        rank_expr = "ts_rank(v.search_vector, plainto_tsquery('spanish', $1)) AS rank"

    total = await conn.fetchval(
        f"SELECT count(*) FROM {LICITACION_VIEW} v {where}",
        *params,
    )

    fetch_limit = body.limit + 1
    data_sql = f"""
        SELECT {DISPLAY_COLS}, {rank_expr}
        FROM {LICITACION_VIEW} v
        {where}
        ORDER BY {order_sql}
        LIMIT ${idx}
    """
    params.append(fetch_limit)

    rows = await conn.fetch(data_sql, *params)
    has_next = len(rows) > body.limit
    if has_next:
        rows = rows[: body.limit]

    # Batch-fetch documents for the result page
    result_ids = [r["id"] for r in rows]
    docs_by_id: dict[object, list[DocumentoResumen]] = {}
    if result_ids:
        doc_rows = await conn.fetch(
            "SELECT licitacion_id, tipo, nombre, url"
            " FROM v_documento WHERE licitacion_id = ANY($1)",
            result_ids,
        )
        for dr in doc_rows:
            docs_by_id.setdefault(dr["licitacion_id"], []).append(
                DocumentoResumen(tipo=dr["tipo"], nombre=dr["nombre"], url=dr["url"])
            )

    resultados = [_row_to_resumen(r, docs_by_id.get(r["id"], [])) for r in rows]

    cursor_siguiente = None
    if has_next and rows:
        last = rows[-1]
        if sort_key == "fecha":
            cursor_siguiente = encode_cursor(last["fecha_actualizacion"], last["id"])
        elif sort_key == "importe":
            cursor_siguiente = encode_cursor(
                last["presupuesto_sin_iva"] or 0, last["id"]
            )
        elif sort_key == "relevancia":
            cursor_siguiente = encode_cursor(last["rank"], last["id"])

    data = RespuestaBusqueda(
        total=total or 0,
        resultados=resultados,
        cursor_siguiente=cursor_siguiente,
    )
    return negotiate(request, data, render_busqueda_md)
