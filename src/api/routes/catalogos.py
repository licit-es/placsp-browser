"""GET /catalogos — discover valid filter values."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from api.deps import get_conn

router = APIRouter(tags=["Catalogos"])

# Map API filter names to catalog tables.
_CATALOG_MAP: dict[str, str] = {
    "tipo_contrato": "cat_type_code",
    "estado": "cat_status_code",
    "procedimiento": "cat_procedure_code",
    "tramitacion": "cat_urgency_code",
    "resultado": "cat_result_code",
    "tipo_organo": "cat_contracting_authority_type",
    "sistema_contratacion": "cat_contracting_system",
    "cpv": "cat_cpv",
    "nuts": "cat_nuts",
    "tipo_documento": "cat_document_type",
    "tipo_criterio": "cat_awarding_criteria_type",
    "tipo_garantia": "cat_guarantee_type",
    "programa_financiacion": "cat_funding_program",
}


@router.get(
    "/catalogos",
    summary="Catalogos disponibles",
)
async def list_catalogos(
    _user: asyncpg.Record = Depends(get_current_user),
) -> dict[str, list[str]]:
    """List available catalog types for filter value discovery."""
    return {"catalogos": sorted(_CATALOG_MAP.keys())}


@router.get(
    "/catalogos/{tipo}",
    summary="Valores de un catalogo",
)
async def get_catalogo(
    tipo: str,
    conn: asyncpg.Connection = Depends(get_conn),
    _user: asyncpg.Record = Depends(get_current_user),
) -> dict[str, object]:
    """Return all values for a catalog type, for filter discovery."""
    table = _CATALOG_MAP.get(tipo)
    if not table:
        raise HTTPException(
            status_code=404,
            detail=f"Catalogo '{tipo}' no encontrado. "
            f"Disponibles: {sorted(_CATALOG_MAP.keys())}",
        )

    rows = await conn.fetch(
        f"SELECT code AS codigo, description AS etiqueta"
        f" FROM {table} WHERE active = true ORDER BY description",
    )
    return {
        "tipo": tipo,
        "valores": [dict(r) for r in rows],
    }
