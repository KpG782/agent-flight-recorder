"""Router stubs matching docs/api-contracts.md paths.

Every feature endpoint returns HTTP 501 Not Implemented at scaffold time. The
owning Wave-1+ agents replace the bodies in-place (paths/shapes are frozen).
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from .schemas import (
    CompareRequest,
    SearchRequest,
    SessionEndRequest,
    SessionStartRequest,
)


def _not_implemented(owner: str, spec: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "code": "not_implemented",
                "message": f"Not implemented yet — owned by {owner} ({spec}).",
            }
        },
    )


# ── Sessions (Phase 1 — CAPTURE) ──
sessions_router = APIRouter(prefix="/sessions", tags=["sessions"])


@sessions_router.post("/start")
async def start_session(_body: SessionStartRequest) -> JSONResponse:
    return _not_implemented("CAPTURE", "phase-1-kill-gate.md")


@sessions_router.post("/{run_id}/end")
async def end_session(run_id: str, _body: SessionEndRequest) -> JSONResponse:
    return _not_implemented("CAPTURE", "phase-1-kill-gate.md")


# ── Search (Phase 1 — INDEX/MEMORY; THE kill-criterion) ──
search_router = APIRouter(tags=["search"])


@search_router.post("/search")
async def search(_body: SearchRequest) -> JSONResponse:
    return _not_implemented("INDEX/MEMORY", "phase-1-kill-gate.md")


# ── Compare (Phase 2 — MEMORY/EVIDENCE) ──
compare_router = APIRouter(prefix="/tasks", tags=["compare"])


@compare_router.post("/{task_name}/compare")
async def compare(task_name: str, _body: CompareRequest) -> JSONResponse:
    return _not_implemented("MEMORY/EVIDENCE", "phase-2-comparison.md")


# ── Explanation (Phase 4 — CLAUDE; SSE) ──
explain_router = APIRouter(prefix="/tasks", tags=["explain"])


@explain_router.get("/{task_name}/explain")
async def explain(task_name: str, query: str = Query(...)) -> JSONResponse:
    return _not_implemented("CLAUDE", "phase-4-claude.md")


# ── Webhooks (Phase 5 — RELIABILITY) ──
webhooks_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@webhooks_router.post("/videodb")
async def videodb_webhook() -> JSONResponse:
    return _not_implemented("RELIABILITY", "phase-5-reliability.md")


ALL_ROUTERS = (
    sessions_router,
    search_router,
    compare_router,
    explain_router,
    webhooks_router,
)
