"""Request/response schemas for authentication and user management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# -------------------------------------------------------------------
# Registration
# -------------------------------------------------------------------


class RegistroPeticion(BaseModel):
    """Registration request."""

    email: EmailStr = Field(description="Correo electronico.")
    nombre: str = Field(min_length=2, max_length=200, description="Nombre del usuario.")
    contrasena: str = Field(min_length=8, max_length=128, description="Contrasena.")


class RegistroRespuesta(BaseModel):
    """Registration response with first API key."""

    id: UUID
    email: str
    nombre: str
    rol: str
    clave_api: str = Field(description="Clave API (se muestra una sola vez).")
    mensaje: str


# -------------------------------------------------------------------
# Login
# -------------------------------------------------------------------


class LoginPeticion(BaseModel):
    """Login request."""

    email: EmailStr = Field(description="Correo electronico.")
    contrasena: str = Field(description="Contrasena.")
    nombre_clave: str | None = Field(
        None,
        max_length=100,
        description="Nombre descriptivo para la nueva clave API.",
    )


class LoginRespuesta(BaseModel):
    """Login response with new API key."""

    id: UUID
    email: str
    nombre: str
    rol: str
    clave_api: str = Field(description="Nueva clave API (se muestra una sola vez).")
    mensaje: str


# -------------------------------------------------------------------
# Profile & key management
# -------------------------------------------------------------------


class PerfilUsuario(BaseModel):
    """Authenticated user profile."""

    id: UUID
    email: str
    nombre: str
    rol: str


class PeticionClave(BaseModel):
    """Request to create a new API key."""

    nombre: str = Field(
        default="nueva_clave",
        max_length=100,
        description="Nombre descriptivo para la clave.",
    )


class ClaveCreada(BaseModel):
    """Response after creating a new API key."""

    clave_api: str = Field(description="Clave API (se muestra una sola vez).")
    mensaje: str


class ClaveResumen(BaseModel):
    """API key summary (never exposes full key)."""

    id: UUID
    key_prefix: str = Field(description="Prefijo de la clave (primeros 8 caracteres).")
    nombre: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None


# -------------------------------------------------------------------
# Admin
# -------------------------------------------------------------------


class UsuarioResumen(BaseModel):
    """User summary for admin listing."""

    id: UUID
    email: str
    nombre: str
    role: str
    is_active: bool
    created_at: datetime


class PatchUsuario(BaseModel):
    """Fields modifiable by admin."""

    is_active: bool | None = None
    rol: Literal["admin", "user"] | None = None


class EntradaAuditoria(BaseModel):
    """Single audit log entry."""

    id: int
    user_id: UUID | None
    usuario_email: str | None
    method: str
    path: str
    status_code: int
    duration_ms: int
    ip_address: str | None
    user_agent: str | None
    request_params: dict[str, Any] | None
    created_at: datetime


class AuditoriaRespuesta(BaseModel):
    """Paginated audit log response."""

    total: int
    registros: list[EntradaAuditoria]
