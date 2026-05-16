"""Upstash Redis wrapper (TLS).

``REDIS_URL`` is a ``rediss://`` URL — the ``rediss`` scheme makes redis-py
negotiate TLS automatically. We use the async client so webhook ack stays fast
(<50ms) and FastAPI handlers never block the event loop.
"""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..logging import get_logger

log = get_logger("afr.redis")

_client: Any | None = None


def get_redis() -> Any:
    """Return the process-wide async redis client (lazily constructed).

    ``rediss://`` ⇒ TLS is enabled by the scheme. We pass decode_responses so
    callers get ``str`` back, and disable health-check intervals chatter.
    """
    global _client
    if _client is not None:
        return _client

    import redis.asyncio as aioredis

    settings = get_settings()
    url = settings.REDIS_URL
    if not url:
        raise RuntimeError("REDIS_URL is not configured")

    _client = aioredis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    log.info("redis_client_created", tls=url.startswith("rediss://"))
    return _client


async def ping() -> bool:
    """PING for /healthz. Raises on failure (caller maps to 'error')."""
    client = get_redis()
    pong = await client.ping()
    return bool(pong)
