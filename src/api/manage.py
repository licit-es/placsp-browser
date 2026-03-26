"""Management commands for the API (create-admin, etc.)."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

import asyncpg

from api.auth import generate_api_key, hash_password
from shared.config import Settings
from shared.logger import get_logger

logger = get_logger(__name__)


async def _create_admin(email: str, nombre: str, password: str) -> None:
    """Create an admin user with an initial API key."""
    settings = Settings()
    pool = await asyncpg.create_pool(settings.database_url)
    if pool is None:
        logger.error("Failed to create connection pool")
        sys.exit(1)
    try:
        pw_hash = hash_password(password)
        plaintext, key_hash, key_prefix = generate_api_key()

        async with pool.acquire() as conn:
            try:
                user_row = await conn.fetchrow(
                    "INSERT INTO api_user"
                    " (email, nombre, password_hash, role)"
                    " VALUES ($1, $2, $3, 'admin')"
                    " RETURNING id, email, nombre, role",
                    email,
                    nombre,
                    pw_hash,
                )
            except asyncpg.UniqueViolationError:
                logger.exception("User with email %s already exists", email)
                sys.exit(1)

            if user_row is None:  # pragma: no cover
                sys.exit(1)
            await conn.execute(
                "INSERT INTO api_key"
                " (user_id, key_hash, key_prefix, nombre)"
                " VALUES ($1, $2, $3, 'admin-initial')",
                user_row["id"],
                key_hash,
                key_prefix,
            )

        logger.info("Admin created: %s <%s>", nombre, email)
        print("\nAdmin user created successfully.")
        print(f"  Email:   {email}")
        print(f"  Name:    {nombre}")
        print(f"  API Key: {plaintext}")
        print("\n  Save this API key. It will not be shown again.\n")
    finally:
        await pool.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="API management commands")
    sub = parser.add_subparsers(dest="command", required=True)

    admin_p = sub.add_parser("create-admin", help="Create an admin user")
    admin_p.add_argument("--email", required=True, help="Admin email address")
    admin_p.add_argument("--nombre", required=True, help="Admin display name")
    admin_p.add_argument(
        "--password",
        default=None,
        help="Password (prompted interactively if omitted)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.command == "create-admin":
        password = args.password or getpass.getpass("Password: ")
        asyncio.run(_create_admin(args.email, args.nombre, password))


if __name__ == "__main__":
    main()
