"""Supabase / Postgres access.

Two surfaces:
- ``get_supabase()``: the supabase-py client (service-role key) for table CRUD
  used by later agents (runs/events/eval_cases per data-model.md).
- ``pg_pool()`` / ``ping()``: a direct asyncpg pool against ``DATABASE_URL`` for
  the migration apply path and the /healthz ``SELECT 1`` probe.

Supabase stores metadata/labels/eval results ONLY (architecture.md hard rule).
Media + scene index live in VideoDB.
"""

from __future__ import annotations

import ssl
from typing import Any

from ..config import get_settings
from ..logging import get_logger

log = get_logger("afr.supabase")

_supabase: Any | None = None
_pool: Any | None = None


def get_supabase() -> Any:
    """Process-wide supabase-py client using the service-role key."""
    global _supabase
    if _supabase is not None:
        return _supabase

    from supabase import create_client

    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not configured")

    _supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )
    log.info("supabase_client_created")
    return _supabase


def _ssl_context() -> ssl.SSLContext:
    """Supabase requires TLS.

    The DIRECT endpoint (db.<ref>.supabase.co) presents a self-signed cert
    chain, so a verifying context fails CERTIFICATE_VERIFY_FAILED. libpq's
    ``sslmode=require`` (encrypt, do not verify) is the documented Supabase
    connection mode for non-PKI clients; we mirror that here. The pooler
    endpoint also accepts this. If a verifying setup is later desired, pin
    Supabase's CA and flip check_hostname/verify_mode back on.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def pg_pool() -> Any:
    """Return a process-wide asyncpg pool against ``DATABASE_URL`` (TLS)."""
    global _pool
    if _pool is not None:
        return _pool

    import urllib.parse as _u

    import asyncpg

    settings = get_settings()
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    # Parse the DSN into explicit components rather than handing the raw string
    # to asyncpg. asyncpg's own DSN parser splits differently from urllib on
    # URL-special characters in the password (e.g. it mis-handled this pooler
    # password, yielding a spurious "password authentication failed"); explicit
    # kwargs are robust against any password character.
    _p = _u.urlparse(settings.DATABASE_URL.strip().strip('"'))

    # Supabase pooler runs PgBouncer in transaction mode; asyncpg must not use
    # prepared statements there (statement_cache_size=0) or it 500s with
    # "prepared statement does not exist". Harmless on a direct connection too.
    _pool = await asyncpg.create_pool(
        user=_u.unquote(_p.username or ""),
        password=_u.unquote(_p.password or ""),
        host=_p.hostname,
        port=_p.port or 5432,
        database=(_p.path or "/postgres").lstrip("/") or "postgres",
        min_size=1,
        max_size=5,
        ssl=_ssl_context(),
        command_timeout=15,
        statement_cache_size=0,
    )
    log.info("pg_pool_created")
    return _pool


async def ping() -> bool:
    """SELECT 1 for /healthz. Raises on failure (caller maps to 'error')."""
    pool = await pg_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval("SELECT 1")
    return val == 1
