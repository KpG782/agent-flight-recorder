"""API routers — real implementations behind the frozen api-contracts.md paths.

Every endpoint logs the observability field set (bound by the service layer)
and maps failures to the standard `{ "error": { "code", "message" } }` envelope.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from . import (
    capture_orchestrator,
    compare_service,
    explain_service,
    search_service,
    webhook_handler,
    ws_broadcaster,
)
from .logging import clear_observability, get_logger
from .schemas import (
    CompareRequest,
    SearchRequest,
    SessionEndRequest,
    SessionStartRequest,
)

log = get_logger("afr.routers")


def _err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


# ── Sessions (Phase 1 — CAPTURE) ──
sessions_router = APIRouter(prefix="/sessions", tags=["sessions"])


@sessions_router.post("/start")
async def start_session(body: SessionStartRequest):
    try:
        return await asyncio.to_thread(capture_orchestrator.start_session, body)
    except Exception as exc:  # noqa: BLE001
        log.warning("start_session_failed", error=str(exc))
        return _err(502, "capture_start_failed", str(exc))
    finally:
        clear_observability()


@sessions_router.post("/{run_id}/end")
async def end_session(run_id: str, body: SessionEndRequest):
    try:
        return await asyncio.to_thread(capture_orchestrator.end_session, run_id, body)
    except LookupError as exc:
        return _err(404, "run_not_found", str(exc))
    except Exception as exc:  # noqa: BLE001
        log.warning("end_session_failed", error=str(exc))
        return _err(502, "capture_end_failed", str(exc))
    finally:
        clear_observability()


# ── Search (Phase 1 — THE kill-criterion) ──
search_router = APIRouter(tags=["search"])


@search_router.post("/search")
async def search(body: SearchRequest):
    try:
        return await asyncio.to_thread(search_service.search, body)
    except LookupError as exc:
        return _err(404, "run_not_found", str(exc))
    except Exception as exc:  # noqa: BLE001
        log.warning("search_failed", error=str(exc))
        return _err(502, "search_failed", str(exc))
    finally:
        clear_observability()


# ── Compare (Phase 2 — MEMORY/EVIDENCE) ──
compare_router = APIRouter(prefix="/tasks", tags=["compare"])


@compare_router.post("/{task_name}/compare")
async def compare(task_name: str, body: CompareRequest):
    try:
        return await asyncio.to_thread(compare_service.compare, task_name, body)
    except (LookupError, KeyError) as exc:
        return _err(404, "compare_unavailable", str(exc))
    except Exception as exc:  # noqa: BLE001
        log.warning("compare_failed", error=str(exc))
        return _err(502, "compare_failed", str(exc))
    finally:
        clear_observability()


# ── Explanation (Phase 4 — CLAUDE; SSE) ──
explain_router = APIRouter(prefix="/tasks", tags=["explain"])


@explain_router.get("/{task_name}/explain")
async def explain(task_name: str, query: str = Query(...)):
    return StreamingResponse(
        explain_service.explain_stream(task_name, query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Webhooks (Phase 5 — RELIABILITY) ──
webhooks_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@webhooks_router.post("/videodb")
async def videodb_webhook(request: Request, background: BackgroundTasks):
    """Ack 200 fast; validate shape; Redis-dedupe on event_id; process async."""
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return _err(400, "bad_payload", "invalid JSON body")

    if not webhook_handler.validate_envelope(payload):
        return _err(400, "bad_envelope", "unrecognized webhook envelope shape")

    if await webhook_handler.is_duplicate(payload):
        log.info("webhook_dedupe_hit", webhook_dedupe_hit=True)
        return JSONResponse(content={"received": True})

    background.add_task(webhook_handler.process_event_async, payload)
    return JSONResponse(content={"received": True})


# ── WebSocket (Phase 3/5) — live event fanout ──
ws_router = APIRouter()


@ws_router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, run_id: str = Query("demo")):
    await ws_broadcaster.register(run_id, websocket)
    feed = asyncio.create_task(ws_broadcaster.replay_feed(run_id))

    def _feed_done(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            log.warning("ws_replay_feed_failed", error=repr(exc))

    feed.add_done_callback(_feed_done)
    try:
        while True:
            await websocket.receive_text()  # keepalive; client sends nothing meaningful
    except WebSocketDisconnect:
        pass
    finally:
        feed.cancel()
        ws_broadcaster.unregister(run_id, websocket)


ALL_ROUTERS = (
    sessions_router,
    search_router,
    compare_router,
    explain_router,
    webhooks_router,
    ws_router,
)
