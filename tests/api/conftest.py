"""Shared fixtures for API tests."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _fake_user() -> dict:
    """Minimal user record matching get_current_user output."""
    return {
        "key_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "id": uuid.uuid4(),
        "email": "test@test.com",
        "nombre": "Test User",
        "role": "admin",
        "is_active": True,
    }


class _FakeRecord(dict):  # type: ignore[type-arg]
    """Dict subclass that supports attribute-style column access like asyncpg.Record."""

    def __getitem__(self, key):  # type: ignore[override]
        return super().__getitem__(key)


@pytest.fixture
def auth_conn() -> AsyncMock:
    """Connection mock shared across auth-aware fixtures."""
    c = AsyncMock()
    c.fetchval = AsyncMock(return_value=1)
    c.fetchrow = AsyncMock(return_value=None)
    c.fetch = AsyncMock(return_value=[])
    c.execute = AsyncMock()
    return c


@pytest.fixture
def auth_client(auth_conn: AsyncMock) -> Iterator[TestClient]:
    """TestClient with auth dependency overridden (all endpoints pass auth)."""
    pool = AsyncMock()
    pool.close = AsyncMock()
    pool.execute = AsyncMock()

    @asynccontextmanager
    async def _acquire():  # type: ignore[no-untyped-def]
        yield auth_conn

    pool.acquire = _acquire

    with patch("api.main.create_pool", return_value=pool):
        from api.auth import get_current_user
        from api.main import app

        user_record = _FakeRecord(_fake_user())

        async def _override_auth():  # type: ignore[no-untyped-def]
            return user_record

        app.dependency_overrides[get_current_user] = _override_auth
        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()
