"""Health check endpoint."""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends

from api.deps import get_pool

router = APIRouter(tags=["Salud"])


@router.get("/salud")
async def health_check(
    pool: asyncpg.Pool = Depends(get_pool),  # noqa: B008
) -> dict[str, str]:
    """Verificar conectividad con la base de datos."""
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:  # noqa: BLE001
        return {"estado": "error", "base_datos": "desconectada"}
    return {"estado": "ok", "base_datos": "conectada"}
