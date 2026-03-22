"""Contracting party (organo contratante) endpoints."""
from __future__ import annotations

import uuid

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_conn
from api.schemas import RespuestaPaginada

router = APIRouter(prefix="/organos-contratantes", tags=["Organos contratantes"])


@router.get(
    "",
    summary="Listar organos contratantes",
    description="Lista paginada de organos contratantes con busqueda por nombre, DIR3 o platform_id.",
)
async def list_parties(
    conn: asyncpg.Connection = Depends(get_conn),
    offset: int = Query(0, ge=0, description="Desplazamiento"),
    limite: int = Query(20, ge=1, le=100, description="Elementos por pagina"),
    busqueda: str | None = Query(None, description="Buscar por nombre, DIR3 o NIF"),
) -> RespuestaPaginada[dict[str, object]]:
    """List contracting parties with search."""
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if busqueda:
        conditions.append(
            f"(p.name ILIKE ${idx} OR p.dir3 ILIKE ${idx} "
            f"OR p.nif ILIKE ${idx} OR p.platform_id ILIKE ${idx})"
        )
        params.append(f"%{busqueda}%")
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = await conn.fetchval(
        f'SELECT count(*) FROM "ContractingParty" p {where}',  # noqa: S608
        *params,
    )

    query = f"""
        SELECT p.*,
               (SELECT count(*) FROM "ContractFolderStatus"
                WHERE contracting_party_id = p.id) AS numero_contratos
        FROM "ContractingParty" p
        {where}
        ORDER BY p.name
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
    "/{organo_id}",
    summary="Detalle de organo contratante",
    description="Detalle de un organo contratante con numero de contratos.",
)
async def get_party(
    organo_id: uuid.UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> dict[str, object]:
    """Get contracting party detail."""
    row = await conn.fetchrow(
        'SELECT * FROM "ContractingParty" WHERE id = $1',
        organo_id,
    )
    if not row:
        raise HTTPException(
            status_code=404, detail="Organo contratante no encontrado"
        )

    result = dict(row)
    result["numero_contratos"] = await conn.fetchval(
        'SELECT count(*) FROM "ContractFolderStatus" WHERE contracting_party_id = $1',
        organo_id,
    )
    return result


@router.get(
    "/{organo_id}/contratos",
    summary="Contratos de un organo contratante",
    description="Lista paginada de contratos de un organo contratante.",
)
async def list_party_contracts(
    organo_id: uuid.UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    offset: int = Query(0, ge=0),
    limite: int = Query(20, ge=1, le=100),
) -> RespuestaPaginada[dict[str, object]]:
    """List contracts for a specific contracting party."""
    total = await conn.fetchval(
        'SELECT count(*) FROM "ContractFolderStatus" WHERE contracting_party_id = $1',
        organo_id,
    )

    rows = await conn.fetch(
        """
        SELECT id, entry_id, title, name, status_code, type_code,
               procedure_code, total_amount, currency_id, updated
        FROM "ContractFolderStatus"
        WHERE contracting_party_id = $1
        ORDER BY updated DESC
        LIMIT $2 OFFSET $3
        """,
        organo_id,
        limite,
        offset,
    )

    return RespuestaPaginada(
        elementos=[dict(r) for r in rows],
        total=total or 0,
        offset=offset,
        limite=limite,
    )
