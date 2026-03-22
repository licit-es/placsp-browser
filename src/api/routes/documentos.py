"""Document reference endpoints."""
from __future__ import annotations

import uuid

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.deps import get_conn
from api.schemas import RespuestaPaginada

router = APIRouter(prefix="/documentos", tags=["Documentos"])


@router.get(
    "",
    summary="Listar documentos",
    description=(
        "Lista paginada de referencias a documentos. "
        "Los agentes pueden usar el campo 'uri' para descargar "
        "directamente desde la PLACSP."
    ),
)
async def list_documents(
    conn: asyncpg.Connection = Depends(get_conn),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    limite: int = Query(20, ge=1, le=100, description="Elementos por pagina"),
    contrato_id: uuid.UUID | None = Query(
        None, description="Filtrar por ID de contrato"
    ),
    tipo_fuente: str | None = Query(
        None, description="Filtrar por source_type (LEGAL, TECHNICAL, etc.)"
    ),
) -> RespuestaPaginada[dict[str, object]]:
    """List document references with filters."""
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if contrato_id:
        conditions.append(f"d.contract_folder_status_id = ${idx}")
        params.append(contrato_id)
        idx += 1
    if tipo_fuente:
        conditions.append(f"d.source_type = ${idx}")
        params.append(tipo_fuente)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = await conn.fetchval(
        f'SELECT count(*) FROM "DocumentReference" d {where}',  # noqa: S608
        *params,
    )

    query = f"""
        SELECT d.*, c.title AS contrato_titulo, c.entry_id AS contrato_entry_id
        FROM "DocumentReference" d
        JOIN "ContractFolderStatus" c ON c.id = d.contract_folder_status_id
        {where}
        ORDER BY d.id
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
