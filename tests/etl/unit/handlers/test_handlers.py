"""Tests for handler wiring — verifies each handler constructs the right result."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from etl.handlers.catalog_updater import _handle as catalog_handle
from etl.handlers.feed_reader import _handle as feed_handle
from shared.models.etl import CatalogUpdateResult, SyncResult


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    """Provide required env vars for Settings() inside handlers."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("ENVIRONMENT", "test")


class TestFeedReaderHandler:
    @pytest.mark.asyncio
    @patch("etl.handlers.feed_reader.asyncpg")
    @patch("etl.handlers.feed_reader.httpx.AsyncClient")
    @patch("etl.handlers.feed_reader.FeedReaderService")
    async def test_returns_aggregated_result(
        self, mock_svc_cls, mock_http_cls, mock_asyncpg
    ) -> None:
        mock_pool = AsyncMock()
        mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

        mock_svc = AsyncMock()
        mock_svc.sync = AsyncMock(
            return_value=SyncResult(processed=10, skipped_stale=2, failed=1, pages=3)
        )
        mock_svc_cls.return_value = mock_svc

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http_cls.return_value = mock_http

        result = await feed_handle({})

        assert result["statusCode"] == 200
        # Both feeds run (outsiders + insiders), each returns 10/1/3
        assert result["body"]["processed"] == 20
        assert result["body"]["failed"] == 2
        assert result["body"]["pages"] == 6


class TestCatalogUpdaterHandler:
    @pytest.mark.asyncio
    @patch("etl.handlers.catalog_updater.asyncpg")
    @patch("etl.handlers.catalog_updater.httpx.AsyncClient")
    @patch("etl.handlers.catalog_updater.CatalogUpdaterService")
    async def test_returns_catalog_result(
        self, mock_svc_cls, mock_http_cls, mock_asyncpg
    ) -> None:
        mock_pool = AsyncMock()
        mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

        mock_svc = AsyncMock()
        mock_svc.sync = AsyncMock(
            return_value=CatalogUpdateResult(
                tables_checked=6, pending_found=3, updated=2, not_found=1
            )
        )
        mock_svc_cls.return_value = mock_svc

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http_cls.return_value = mock_http

        result = await catalog_handle({"root_url": "https://example.com/"})

        assert result["statusCode"] == 200
        assert result["body"]["updated"] == 2
        assert result["body"]["not_found"] == 1
