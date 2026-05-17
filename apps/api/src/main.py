"""FastAPI application entrypoint.

Wires structlog, registers the (501) router stubs that match
docs/api-contracts.md, and exposes a real `GET /healthz` that actively pings
VideoDB, Redis and Supabase/Postgres.

Run: `uvicorn src.main:app --reload` from apps/api (or `--app-dir apps/api`).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .clients import redis_client, supabase_client, videodb_client
from .config import get_settings
from .logging import configure_logging, get_logger
from .routers import ALL_ROUTERS
from .schemas import HealthzResponse

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
log = get_logger("afr.main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info(
        "api_starting",
        replay_mode=settings.REPLAY_MODE,
        demo_task_name=settings.DEMO_TASK_NAME,
        capture_frame_interval_s=settings.CAPTURE_FRAME_INTERVAL_S,
    )
    yield
    log.info("api_stopping")


app = FastAPI(
    title="Agent Flight Recorder API",
    version="0.1.0",
    description="Forensic black-box recorder for agent/app runs (VideoDB hackathon).",
    lifespan=lifespan,
)

# Local demo: Next.js on :3000 calls this API on :8000. Permissive CORS is
# acceptable for a localhost hackathon demo (no credentialed cross-site auth).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in ALL_ROUTERS:
    app.include_router(router)


async def _probe(name: str, coro_or_callable, is_async: bool) -> str:
    """Run one health probe; return 'ok' or 'error: <reason>'. Never raises."""
    try:
        if is_async:
            ok = await asyncio.wait_for(coro_or_callable(), timeout=10)
        else:
            ok = await asyncio.wait_for(
                asyncio.to_thread(coro_or_callable), timeout=15
            )
        return "ok" if ok else "error: probe returned falsy"
    except Exception as exc:  # noqa: BLE001 — health must never crash
        log.warning("healthz_probe_failed", probe=name, error=str(exc))
        return f"error: {type(exc).__name__}"


@app.get("/healthz", response_model=HealthzResponse)
async def healthz() -> HealthzResponse:
    """Liveness + dependency readiness.

    - videodb: authenticated connect + get_collection
    - redis: PING (TLS rediss://)
    - supabase/postgres: SELECT 1 over asyncpg
    """
    videodb_status, redis_status, supabase_status = await asyncio.gather(
        _probe("videodb", videodb_client.ping, is_async=False),
        _probe("redis", redis_client.ping, is_async=True),
        _probe("supabase", supabase_client.ping, is_async=True),
    )

    overall = (
        "ok"
        if all(
            s == "ok" for s in (videodb_status, redis_status, supabase_status)
        )
        else "degraded"
    )

    return HealthzResponse(
        status=overall,
        replay_mode=settings.REPLAY_MODE,
        videodb=videodb_status,
        redis=redis_status,
        supabase=supabase_status,
    )
