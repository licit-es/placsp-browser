"""GET /similares/{id} — structurally similar tenders."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.catalogs import to_codes
from api.deps import get_conn
from api.schemas import LicitacionResumen

router = APIRouter(tags=["Similares"])


@router.get(
    "/similares/{licitacion_id}",
    response_model=list[LicitacionResumen],
    summary="Licitaciones similares resueltas",
)
async def get_similares(
    licitacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),  # type: ignore[assignment]
    estado: str | None = Query(None, description="Filtrar por estado"),
    rango_importe_pct: int = Query(50, ge=10, le=200),
    limit: int = Query(10, ge=1, le=50),
) -> list[LicitacionResumen]:
    """Find structurally similar tenders by CPV prefix + amount range."""
    # Get reference tender from view
    ref = await conn.fetchrow(
        "SELECT presupuesto_sin_iva, type_code, cpv_principal"
        " FROM v_licitacion WHERE id = $1",
        licitacion_id,
    )
    if not ref:
        raise HTTPException(status_code=404, detail="Licitacion no encontrada")

    cpv = ref["cpv_principal"]
    amount = ref["presupuesto_sin_iva"]
    tipo = ref["type_code"]

    # Build similarity query
    conditions = ["v.id != $1"]
    params: list[object] = [licitacion_id]
    idx = 2

    # Same CPV prefix (first 3-5 digits depending on specificity)
    if cpv:
        cpv_prefix_len = 5
        prefix = cpv[:cpv_prefix_len] if len(cpv) >= cpv_prefix_len else cpv
        conditions.append(
            f"EXISTS (SELECT 1 FROM v_cpv vc"
            f" WHERE vc.licitacion_id = v.id"
            f" AND vc.codigo LIKE ${idx})"
        )
        params.append(f"{prefix}%")
        idx += 1

    # Same type (raw code for indexed match)
    if tipo:
        conditions.append(f"v.type_code = ${idx}")
        params.append(tipo)
        idx += 1

    # Amount range
    if amount:
        factor = rango_importe_pct / 100
        lo = float(amount) * (1 - factor)
        hi = float(amount) * (1 + factor)
        conditions.append(
            f"v.presupuesto_sin_iva BETWEEN ${idx} AND ${idx + 1}"
        )
        params.extend([lo, hi])
        idx += 2

    if estado:
        conditions.append(f"v.status_code = ${idx}")
        params.append(to_codes("estado", [estado])[0])
        idx += 1

    where = "WHERE " + " AND ".join(conditions)

    rows = await conn.fetch(
        f"""
        SELECT v.id, v.expediente, v.titulo, v.organo,
               v.tipo_contrato, v.estado, v.presupuesto_sin_iva,
               v.importe_adjudicacion, v.fecha_publicacion,
               v.fecha_adjudicacion, v.cpv_principal,
               v.num_licitadores, v.adjudicatario,
               v.lugar_subentidad AS lugar,
               v.tiene_documentos, v.num_lotes
        FROM v_licitacion v
        {where}
        ORDER BY v.fecha_publicacion DESC
        LIMIT ${idx}
        """,
        *params,
        limit,
    )

    return [
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
        for r in rows
    ]
