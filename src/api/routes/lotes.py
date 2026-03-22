"""Lot (lote) endpoints."""
from __future__ import annotations

from decimal import Decimal

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.deps import get_conn
from api.schemas import RespuestaPaginada

router = APIRouter(prefix="/lotes", tags=["Lotes"])


@router.get(
    "",
    summary="Listar lotes",
    description="Lista paginada de lotes con filtros por codigo CPV y rango de importe.",
)
async def list_lots(
    conn: asyncpg.Connection = Depends(get_conn),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    limite: int = Query(20, ge=1, le=100, description="Elementos por pagina"),
    cpv: str | None = Query(None, description="Filtrar por codigo CPV"),
    importe_min: Decimal | None = Query(None, description="Importe minimo"),
    importe_max: Decimal | None = Query(None, description="Importe maximo"),
) -> RespuestaPaginada[dict[str, object]]:
    """List lots with CPV and amount filters."""
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if cpv:
        conditions.append(
            f"""EXISTS (
                SELECT 1 FROM cpv_classification cv
                WHERE cv.lot_id = l.id
                AND cv.item_classification_code LIKE ${idx}
            )"""
        )
        params.append(f"{cpv}%")
        idx += 1
    if importe_min is not None:
        conditions.append(f"l.total_amount >= ${idx}")
        params.append(importe_min)
        idx += 1
    if importe_max is not None:
        conditions.append(f"l.total_amount <= ${idx}")
        params.append(importe_max)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = await conn.fetchval(
        f'SELECT count(*) FROM procurement_project_lot l {where}',  # noqa: S608
        *params,
    )

    query = f"""
        SELECT l.*, c.title AS contrato_titulo, c.status_code,
               c.entry_id AS contrato_entry_id
        FROM procurement_project_lot l
        JOIN contract_folder_status c ON c.id = l.contract_folder_status_id
        {where}
        ORDER BY l.total_amount DESC NULLS LAST
        LIMIT ${idx} OFFSET ${idx + 1}
    """  # noqa: S608
    params.extend([limite, offset])
    rows = await conn.fetch(query, *params)

    return RespuestaPaginada(
        elementos=[dict(r) for r in rows],
        total=total or 0,
        offset=offset,
        limite=limite,
    )
