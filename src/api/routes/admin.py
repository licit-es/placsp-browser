"""Admin endpoints: user management and audit log queries."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import require_admin
from api.deps import get_conn
from api.schemas.auth import (
    AuditoriaRespuesta,
    EntradaAuditoria,
    PatchUsuario,
    UsuarioResumen,
)

router = APIRouter(prefix="/admin", tags=["Administracion"])


@router.get(
    "/usuarios",
    response_model=list[UsuarioResumen],
    summary="Listar usuarios",
)
async def listar_usuarios(
    _admin: asyncpg.Record = Depends(require_admin),
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[UsuarioResumen]:
    """List all registered users."""
    rows = await conn.fetch(
        "SELECT id, email, nombre, role, is_active, created_at"
        " FROM api_user ORDER BY created_at DESC"
    )
    return [UsuarioResumen(**dict(r)) for r in rows]


@router.patch(
    "/usuarios/{usuario_id}",
    response_model=UsuarioResumen,
    summary="Modificar usuario (activar/desactivar, cambiar rol)",
)
async def patch_usuario(
    usuario_id: UUID,
    body: PatchUsuario,
    _admin: asyncpg.Record = Depends(require_admin),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UsuarioResumen:
    """Activate/deactivate user or change role."""
    sets: list[str] = []
    params: list[object] = [usuario_id]
    idx = 2  # $1 is usuario_id

    if body.is_active is not None:
        sets.append(f"is_active = ${idx}")
        params.append(body.is_active)
        idx += 1
    if body.rol is not None:
        sets.append(f"role = ${idx}")
        params.append(body.rol)
        idx += 1

    if not sets:
        raise HTTPException(status_code=400, detail="No hay campos a modificar")

    sets.append("updated_at = now()")
    sql = (
        f"UPDATE api_user SET {', '.join(sets)}"
        f" WHERE id = $1"
        f" RETURNING id, email, nombre, role, is_active, created_at"
    )

    row = await conn.fetchrow(sql, *params)
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UsuarioResumen(**dict(row))


@router.get(
    "/auditoria",
    response_model=AuditoriaRespuesta,
    summary="Consultar registros de auditoria",
)
async def auditoria(
    _admin: asyncpg.Record = Depends(require_admin),
    conn: asyncpg.Connection = Depends(get_conn),
    usuario_id: UUID | None = Query(None),
    path: str | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AuditoriaRespuesta:
    """Query audit logs with filters and pagination."""
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if usuario_id:
        conditions.append(f"a.user_id = ${idx}")
        params.append(usuario_id)
        idx += 1
    if path:
        conditions.append(f"a.path LIKE ${idx}")
        params.append(f"%{path}%")
        idx += 1
    if desde:
        conditions.append(f"a.created_at >= ${idx}")
        params.append(desde)
        idx += 1
    if hasta:
        conditions.append(f"a.created_at < ${idx}::date + 1")
        params.append(hasta)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = await conn.fetchval(f"SELECT count(*) FROM audit_log a {where}", *params)

    rows = await conn.fetch(
        f"SELECT a.id, a.user_id, u.email AS usuario_email,"
        f" a.method, a.path, a.status_code, a.duration_ms,"
        f" a.ip_address, a.user_agent, a.request_params, a.created_at"
        f" FROM audit_log a"
        f" LEFT JOIN api_user u ON u.id = a.user_id"
        f" {where}"
        f" ORDER BY a.created_at DESC"
        f" LIMIT ${idx} OFFSET ${idx + 1}",
        *params,
        limit,
        offset,
    )

    return AuditoriaRespuesta(
        total=total or 0,
        registros=[
            EntradaAuditoria(
                **{
                    **dict(r),
                    "ip_address": str(r["ip_address"]) if r["ip_address"] else None,
                }
            )
            for r in rows
        ],
    )


@router.delete(
    "/usuarios/{usuario_id}/claves",
    status_code=204,
    summary="Revocar todas las claves de un usuario",
)
async def revocar_claves_usuario(
    usuario_id: UUID,
    _admin: asyncpg.Record = Depends(require_admin),
    conn: asyncpg.Connection = Depends(get_conn),
) -> None:
    """Revoke all API keys for a user (admin action)."""
    result = await conn.execute(
        "UPDATE api_key SET is_active = false WHERE user_id = $1 AND is_active = true",
        usuario_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="No se encontraron claves activas")
