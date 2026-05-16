"""VideoDB SDK wrapper.

``videodb.connect()`` auto-reads ``VIDEO_DB_API_KEY`` from the environment; we
additionally pass ``base_url`` from ``VIDEO_DB_BASE_URL`` (Wave 0 recon). The
``Connection`` is a stateless REST wrapper — reuse one per process (cheatsheet
§1). This wrapper adds a retry/backoff helper (max 3 attempts) for transient
errors, used by later agents around capture/index/search calls.
"""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from ..config import get_settings
from ..logging import get_logger

log = get_logger("afr.videodb")

T = TypeVar("T")

# Connection is cached at module scope (reuse one per process).
_conn: Any | None = None

# Transient error markers we retry on (HTTP 5xx-ish / network).
_RETRYABLE_SUBSTRINGS = ("502", "503", "504", "timeout", "temporarily", "connection")
_MAX_ATTEMPTS = 3
_BASE_BACKOFF_S = 0.5


def get_connection() -> Any:
    """Return the process-wide VideoDB ``Connection``, connecting on first use.

    ``VIDEO_DB_API_KEY`` is read from the environment by the SDK; we pass
    ``base_url`` explicitly from ``VIDEO_DB_BASE_URL``.
    """
    global _conn
    if _conn is not None:
        return _conn

    import videodb  # imported lazily so the module is importable without network

    settings = get_settings()
    _conn = videodb.connect(
        api_key=settings.VIDEO_DB_API_KEY or None,
        base_url=settings.VIDEO_DB_BASE_URL,
    )
    log.info("videodb_connected", base_url=settings.VIDEO_DB_BASE_URL)
    return _conn


def ping() -> bool:
    """Lightweight connectivity check for /healthz.

    Establishing a ``Connection`` performs an authenticated handshake against
    ``VIDEO_DB_BASE_URL``; if that succeeds we consider VideoDB reachable.
    """
    conn = get_connection()
    # get_collection() is a cheap authenticated round-trip.
    conn.get_collection("default")
    return True


def with_retry(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run ``fn(*args, **kwargs)`` with up to 3 attempts and exponential
    backoff on transient errors. Non-transient errors raise immediately.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — classify by message
            msg = str(exc).lower()
            transient = any(s in msg for s in _RETRYABLE_SUBSTRINGS)
            last_exc = exc
            if not transient or attempt == _MAX_ATTEMPTS:
                raise
            backoff = _BASE_BACKOFF_S * (2 ** (attempt - 1))
            log.warning(
                "videodb_retry",
                attempt=attempt,
                max_attempts=_MAX_ATTEMPTS,
                backoff_s=backoff,
                error=str(exc),
            )
            time.sleep(backoff)
    assert last_exc is not None
    raise last_exc
