"""Apply SQL migrations against DATABASE_URL.

Usage (from apps/api):  .venv/bin/python migrations/apply.py

Idempotent — every statement in 0001_init.sql uses IF NOT EXISTS. Uses the
project's asyncpg pool wrapper (TLS, sslmode=require equivalent). Run this once
the correct Supabase DB password is in .env's DATABASE_URL.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.clients.supabase_client import pg_pool  # noqa: E402
from src.logging import configure_logging, get_logger  # noqa: E402

configure_logging("INFO")
log = get_logger("afr.migrate")

MIGRATIONS_DIR = pathlib.Path(__file__).parent


async def main() -> None:
    pool = await pg_pool()
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for f in files:
        sql = f.read_text()
        log.info("applying_migration", file=f.name)
        async with pool.acquire() as conn:
            await conn.execute(sql)
        log.info("applied_migration", file=f.name)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        )
    log.info("public_tables", tables=[r["table_name"] for r in rows])


if __name__ == "__main__":
    asyncio.run(main())
