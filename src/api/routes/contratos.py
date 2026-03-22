"""Contract listing and detail endpoints."""
from __future__ import annotations

import uuid

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_conn
from api.schemas import RespuestaPaginada

router = APIRouter(prefix="/contratos", tags=["Contratos"])


@router.get(
    "",
    summary="Listar contratos",
    description=(
        "Lista paginada de contratos con filtros opcionales por estado, "
        "tipo, procedimiento, fechas y busqueda por titulo."
    ),
)
async def list_contracts(
    conn: asyncpg.Connection = Depends(get_conn),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    limite: int = Query(20, ge=1, le=100, description="Elementos por pagina"),
    estado: str | None = Query(None, description="Filtrar por status_code"),
    tipo: str | None = Query(None, description="Filtrar por type_code"),
    procedimiento: str | None = Query(None, description="Filtrar por procedure_code"),
    busqueda: str | None = Query(None, description="Buscar en titulo y nombre"),
) -> RespuestaPaginada[dict[str, object]]:
    """List contracts with pagination and filtering."""
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if estado:
        conditions.append(f"c.status_code = ${idx}")
        params.append(estado)
        idx += 1
    if tipo:
        conditions.append(f"c.type_code = ${idx}")
        params.append(tipo)
        idx += 1
    if procedimiento:
        conditions.append(f"c.procedure_code = ${idx}")
        params.append(procedimiento)
        idx += 1
    if busqueda:
        conditions.append(
            f"(c.title ILIKE ${idx} OR c.name ILIKE ${idx})"
        )
        params.append(f"%{busqueda}%")
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_sql = f'SELECT count(*) FROM contract_folder_status c {where}'  # noqa: S608
    total = await conn.fetchval(count_sql, *params)

    query = f"""
        SELECT c.id, c.entry_id, c.title, c.name, c.status_code,
               c.type_code, c.procedure_code, c.total_amount, c.currency_id,
               c.nuts_code, c.updated, c.contract_folder_id,
               p.name AS organo_contratante
        FROM contract_folder_status c
        LEFT JOIN contracting_party p ON p.id = c.contracting_party_id
        {where}
        ORDER BY c.updated DESC
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


@router.get(
    "/{contrato_id}",
    summary="Detalle de contrato",
    description="Detalle completo de un contrato con lotes, resultados y documentos.",
)
async def get_contract(
    contrato_id: uuid.UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> dict[str, object]:
    """Get full contract detail with nested children."""
    row = await conn.fetchrow(
        """
        SELECT c.*, p.name AS organo_contratante_nombre,
               p.nif AS organo_contratante_nif,
               p.dir3 AS organo_contratante_dir3
        FROM contract_folder_status c
        LEFT JOIN contracting_party p ON p.id = c.contracting_party_id
        WHERE c.id = $1
        """,
        contrato_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")

    contract = dict(row)

    lotes = await conn.fetch(
        'SELECT * FROM procurement_project_lot WHERE contract_folder_status_id = $1',
        contrato_id,
    )
    resultados = await conn.fetch(
        """
        SELECT tr.*, wp.name AS adjudicatario_nombre, wp.identifier AS adjudicatario_nif
        FROM tender_result tr
        LEFT JOIN LATERAL (
            SELECT name, identifier FROM winning_party
            WHERE tender_result_id = tr.id LIMIT 1
        ) wp ON true
        WHERE tr.contract_folder_status_id = $1
        """,
        contrato_id,
    )
    documentos = await conn.fetch(
        'SELECT * FROM document_reference WHERE contract_folder_status_id = $1',
        contrato_id,
    )

    contract["lotes"] = [dict(r) for r in lotes]
    contract["resultados"] = [dict(r) for r in resultados]
    contract["documentos"] = [dict(r) for r in documentos]

    return contract
