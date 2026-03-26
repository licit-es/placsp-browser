"""Health endpoint tests."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Create a test client with a mocked db pool."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)

    pool = AsyncMock()
    pool.close = AsyncMock()
    pool.execute = AsyncMock()

    @asynccontextmanager
    async def _acquire():  # type: ignore[no-untyped-def]
        yield conn

    pool.acquire = _acquire

    with patch("api.main.create_pool", return_value=pool):
        from api.main import app

        with TestClient(app) as c:
            yield c


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/salud")
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "ok"
    assert data["base_datos"] == "conectada"


def test_openapi_available(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "PLACSP API"
    assert "/salud" in schema["paths"]
    assert "/v1/buscar" in schema["paths"]
    assert "/v1/licitacion/{licitacion_id}" in schema["paths"]
