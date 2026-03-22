"""Catalog updater handler — CLI entry point."""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg
import httpx

from shared.config import Settings
from shared.logger import get_logger
from etl.repositories.catalog_repo import PgCatalogRepository
from etl.services.catalog_updater import CatalogUpdaterService

logger = get_logger(__name__)


async def _handle(event: dict[str, Any]) -> dict[str, Any]:
    config = Settings()
    root_url = event.get("root_url")

    pool = await asyncpg.create_pool(config.database_url)
    try:
        catalog_repo = PgCatalogRepository(pool)

        async with httpx.AsyncClient() as http:
            svc = CatalogUpdaterService(
                catalog_repo=catalog_repo,
                http_client=http,
                config=config,
            )
            result = await svc.sync(root_url=root_url)

    finally:
        await pool.close()

    logger.info(
        "Catalog update done tables_checked=%d pending=%d updated=%d not_found=%d",
        result.tables_checked,
        result.pending_found,
        result.updated,
        result.not_found,
    )

    return {
        "statusCode": 200,
        "body": {
            "tables_checked": result.tables_checked,
            "pending_found": result.pending_found,
            "updated": result.updated,
            "not_found": result.not_found,
        },
    }


def main() -> None:
    try:
        result = asyncio.run(_handle({}))
        logger.info("Result: %s", result)
    except KeyboardInterrupt:
        logger.info("Interrupted")


if __name__ == "__main__":
    main()
