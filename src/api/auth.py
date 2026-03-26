"""Authentication: password hashing, API key management, FastAPI deps."""

from __future__ import annotations

import hashlib
import secrets
from base64 import urlsafe_b64encode

import asyncpg
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.deps import get_conn

_KEY_PREFIX = "licit_"
_KEY_RANDOM_BYTES = 32

_bearer_scheme = HTTPBearer(auto_error=False)


# -------------------------------------------------------------------
# Password hashing (bcrypt) — registration and login only
# -------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# -------------------------------------------------------------------
# API key generation and verification (SHA-256) — every request
# -------------------------------------------------------------------


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns (plaintext_key, sha256_hash, key_prefix).
    The plaintext is shown once to the user and never stored.
    """
    random_part = (
        urlsafe_b64encode(secrets.token_bytes(_KEY_RANDOM_BYTES)).decode().rstrip("=")
    )
    plaintext = f"{_KEY_PREFIX}{random_part}"
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    key_prefix = random_part[:8]
    return plaintext, key_hash, key_prefix


def _hash_key(plaintext: str) -> str:
    """Hash an API key using SHA-256 for DB lookup."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


# -------------------------------------------------------------------
# FastAPI dependencies
# -------------------------------------------------------------------


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    conn: asyncpg.Connection = Depends(get_conn),
) -> asyncpg.Record:
    """Validate Bearer token and return the user record.

    Stores user_id and api_key_id in request.state for audit middleware.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticacion requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_hash = _hash_key(credentials.credentials)
    row = await conn.fetchrow(
        "SELECT ak.id AS key_id, ak.user_id,"
        " u.id, u.email, u.nombre, u.role, u.is_active"
        " FROM api_key ak"
        " JOIN api_user u ON u.id = ak.user_id"
        " WHERE ak.key_hash = $1"
        "   AND ak.is_active = true"
        "   AND (ak.expires_at IS NULL OR ak.expires_at > now())"
        "   AND u.is_active = true",
        key_hash,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave API invalida o expirada",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fire-and-forget: update last_used_at
    await conn.execute(
        "UPDATE api_key SET last_used_at = now() WHERE id = $1",
        row["key_id"],
    )

    # Store in request.state for audit middleware
    request.state.user_id = row["user_id"]
    request.state.api_key_id = row["key_id"]

    return row


async def require_admin(
    user: asyncpg.Record = Depends(get_current_user),
) -> asyncpg.Record:
    """Require the current user to have admin role."""
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return user
