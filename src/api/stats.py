"""Daily API usage stats — queries audit_log and prints a JSON report."""

from __future__ import annotations

import asyncio
import json
import sys

import asyncpg

from shared.config import Settings
from shared.logger import get_logger

logger = get_logger(__name__)


async def _gather_stats(pool: asyncpg.Pool) -> dict[str, object]:
    """Query last-24h metrics from audit_log and api_user tables."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT"
            "  count(*) AS total_requests,"
            "  count(DISTINCT user_id) AS active_users,"
            "  count(*) FILTER ("
            "    WHERE status_code >= 400 AND status_code < 500"
            "  ) AS client_errors,"
            "  count(*) FILTER (WHERE status_code >= 500)"
            "    AS server_errors,"
            "  round(avg(duration_ms)) AS mean_latency_ms,"
            "  percentile_cont(0.95) WITHIN GROUP"
            "    (ORDER BY duration_ms)::int AS p95_latency_ms,"
            "  count(*) FILTER (WHERE status_code = 401) AS auth_failures"
            " FROM audit_log"
            " WHERE created_at >= now() - interval '24 hours'"
        )

        top_endpoints = await conn.fetch(
            "SELECT path, count(*) AS hits"
            " FROM audit_log"
            " WHERE created_at >= now() - interval '24 hours'"
            " GROUP BY path ORDER BY hits DESC LIMIT 5"
        )

        peak_hour = await conn.fetchrow(
            "SELECT extract(hour FROM created_at)::int AS hora, count(*) AS hits"
            " FROM audit_log"
            " WHERE created_at >= now() - interval '24 hours'"
            " GROUP BY hora ORDER BY hits DESC LIMIT 1"
        )

        top_users = await conn.fetch(
            "SELECT u.email, count(*) AS hits"
            " FROM audit_log a"
            " JOIN api_user u ON u.id = a.user_id"
            " WHERE a.created_at >= now() - interval '24 hours'"
            " GROUP BY u.email ORDER BY hits DESC LIMIT 3"
        )

        new_users = await conn.fetchval(
            "SELECT count(*) FROM api_user"
            " WHERE created_at >= now() - interval '24 hours'"
        )

        total_users = await conn.fetchval("SELECT count(*) FROM api_user")

    total = row["total_requests"] or 0
    active = row["active_users"] or 0
    mean_per_user = round(total / active, 1) if active else 0

    return {
        "total_requests": total,
        "active_users": active,
        "mean_per_user": mean_per_user,
        "mean_latency_ms": int(row["mean_latency_ms"] or 0),
        "p95_latency_ms": int(row["p95_latency_ms"] or 0),
        "client_errors": row["client_errors"] or 0,
        "server_errors": row["server_errors"] or 0,
        "auth_failures": row["auth_failures"] or 0,
        "error_rate_pct": round(
            ((row["client_errors"] or 0) + (row["server_errors"] or 0)) / total * 100,
            1,
        )
        if total
        else 0,
        "new_users_24h": new_users or 0,
        "total_users": total_users or 0,
        "peak_hour": f"{peak_hour['hora']:02d}:00" if peak_hour else "-",
        "peak_hour_hits": peak_hour["hits"] if peak_hour else 0,
        "top_endpoints": [
            {"path": r["path"], "hits": r["hits"]} for r in top_endpoints
        ],
        "top_users": [{"email": r["email"], "hits": r["hits"]} for r in top_users],
    }


async def _main() -> None:
    settings = Settings()
    pool = await asyncpg.create_pool(settings.database_url)
    if pool is None:
        logger.error("Failed to create connection pool")
        sys.exit(1)
    try:
        stats = await _gather_stats(pool)
        print(json.dumps(stats))
    finally:
        await pool.close()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
