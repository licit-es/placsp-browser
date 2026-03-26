"""Audit logging middleware."""

from __future__ import annotations

import json
import time

import asyncpg
from fastapi import Request, Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from shared.logger import get_logger

logger = get_logger(__name__)

_SKIP_PATHS = frozenset(
    {
        "/salud",
        "/openapi.json",
        "/docs",
        "/redoc",
        "/",
        "/registro",
        "/iniciar-sesion",
        "/panel",
    }
)


class AuditMiddleware(BaseHTTPMiddleware):
    """Log every API request to the audit_log table."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path in _SKIP_PATHS or path.startswith("/static"):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        user_id = getattr(request.state, "user_id", None)
        api_key_id = getattr(request.state, "api_key_id", None)
        search_params = getattr(request.state, "search_params", None)

        # Serialize search_params dict to JSON string for asyncpg
        params_json: str | None = None
        if search_params is not None:
            params_json = json.dumps(search_params, default=str)

        # Extract client IP (Caddy sets X-Forwarded-For)
        ip_raw = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not ip_raw and request.client:
            ip_raw = request.client.host
        ip_address = ip_raw or None

        user_agent = request.headers.get("user-agent")

        try:
            pool: asyncpg.Pool = request.app.state.pool
            await pool.execute(
                "INSERT INTO audit_log"
                " (user_id, api_key_id, method, path, status_code,"
                "  duration_ms, ip_address, user_agent, request_params)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7::inet, $8, $9::jsonb)",
                user_id,
                api_key_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                ip_address,
                user_agent,
                params_json,
            )
        except Exception:
            logger.exception("Failed to write audit log")

        return response
