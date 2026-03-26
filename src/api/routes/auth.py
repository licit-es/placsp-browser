"""Auth endpoints: registration, login, key management."""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import (
    generate_api_key,
    get_current_user,
    hash_password,
    verify_password,
)
from api.deps import get_conn
from api.schemas.auth import (
    ClaveCreada,
    ClaveResumen,
    LoginPeticion,
    LoginRespuesta,
    PerfilUsuario,
    PeticionClave,
    RegistroPeticion,
    RegistroRespuesta,
)

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


# -------------------------------------------------------------------
# Public endpoints
# -------------------------------------------------------------------


@router.post(
    "/registro",
    response_model=RegistroRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registro de nuevo usuario",
)
async def registro(
    body: RegistroPeticion,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RegistroRespuesta:
    """Register a new user. Returns user info and first API key."""
    pw_hash = hash_password(body.contrasena)
    plaintext, key_hash, key_prefix = generate_api_key()

    try:
        user_row = await conn.fetchrow(
            "INSERT INTO api_user (email, nombre, password_hash)"
            " VALUES ($1, $2, $3)"
            " RETURNING id, email, nombre, role, created_at",
            body.email,
            body.nombre,
            pw_hash,
        )
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        ) from exc

    if user_row is None:  # pragma: no cover — INSERT RETURNING always returns
        raise HTTPException(status_code=500, detail="Error interno")
    await conn.execute(
        "INSERT INTO api_key (user_id, key_hash, key_prefix, nombre)"
        " VALUES ($1, $2, $3, 'default')",
        user_row["id"],
        key_hash,
        key_prefix,
    )

    return RegistroRespuesta(
        id=user_row["id"],
        email=user_row["email"],
        nombre=user_row["nombre"],
        rol=user_row["role"],
        clave_api=plaintext,
        mensaje="Guarda esta clave API. No se mostrara de nuevo.",
    )


@router.post(
    "/login",
    response_model=LoginRespuesta,
    summary="Iniciar sesion y obtener nueva clave API",
)
async def login(
    body: LoginPeticion,
    conn: asyncpg.Connection = Depends(get_conn),
) -> LoginRespuesta:
    """Authenticate with email+password, returns a new API key."""
    user = await conn.fetchrow(
        "SELECT id, email, nombre, role, password_hash, is_active"
        " FROM api_user WHERE email = $1",
        body.email,
    )
    if not user or not verify_password(body.contrasena, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )

    plaintext, key_hash, key_prefix = generate_api_key()
    key_name = body.nombre_clave or "login"
    await conn.execute(
        "INSERT INTO api_key (user_id, key_hash, key_prefix, nombre)"
        " VALUES ($1, $2, $3, $4)",
        user["id"],
        key_hash,
        key_prefix,
        key_name,
    )

    return LoginRespuesta(
        id=user["id"],
        email=user["email"],
        nombre=user["nombre"],
        rol=user["role"],
        clave_api=plaintext,
        mensaje="Nueva clave API generada. No se mostrara de nuevo.",
    )


# -------------------------------------------------------------------
# Authenticated endpoints
# -------------------------------------------------------------------


@router.get(
    "/perfil",
    response_model=PerfilUsuario,
    summary="Ver perfil del usuario autenticado",
)
async def perfil(
    user: asyncpg.Record = Depends(get_current_user),
) -> PerfilUsuario:
    """Return the authenticated user's profile."""
    return PerfilUsuario(
        id=user["id"],
        email=user["email"],
        nombre=user["nombre"],
        rol=user["role"],
    )


@router.get(
    "/claves",
    response_model=list[ClaveResumen],
    summary="Listar claves API propias",
)
async def listar_claves(
    user: asyncpg.Record = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[ClaveResumen]:
    """List the authenticated user's API keys (prefix only)."""
    rows = await conn.fetch(
        "SELECT id, key_prefix, nombre, is_active,"
        " created_at, last_used_at"
        " FROM api_key WHERE user_id = $1"
        " ORDER BY created_at DESC",
        user["user_id"],
    )
    return [ClaveResumen(**dict(r)) for r in rows]


@router.post(
    "/claves",
    response_model=ClaveCreada,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva clave API",
)
async def crear_clave(
    body: PeticionClave,
    user: asyncpg.Record = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> ClaveCreada:
    """Create an additional API key for the authenticated user."""
    plaintext, key_hash, key_prefix = generate_api_key()
    await conn.execute(
        "INSERT INTO api_key (user_id, key_hash, key_prefix, nombre)"
        " VALUES ($1, $2, $3, $4)",
        user["user_id"],
        key_hash,
        key_prefix,
        body.nombre,
    )
    return ClaveCreada(
        clave_api=plaintext,
        mensaje="Guarda esta clave API. No se mostrara de nuevo.",
    )


@router.delete(
    "/claves/{clave_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revocar una clave API propia",
)
async def revocar_clave(
    clave_id: UUID,
    user: asyncpg.Record = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> None:
    """Deactivate one of the authenticated user's API keys."""
    result = await conn.execute(
        "UPDATE api_key SET is_active = false WHERE id = $1 AND user_id = $2",
        clave_id,
        user["user_id"],
    )
    if result == "UPDATE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clave no encontrada",
        )
