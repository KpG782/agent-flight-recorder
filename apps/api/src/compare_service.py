"""`/tasks/{task_name}/compare` orchestration (Wave 2).

Ties MEMORY (first-divergence) + EVIDENCE (per-run clips) into the frozen
CompareResponse (api-contracts.md). `explanation` is left null — it is filled
by the Phase-4 SSE endpoint, not inline.
"""

from __future__ import annotations

import time

from . import evidence_compiler, memory_router
from .logging import bind_observability, get_logger
from .schemas import CompareRequest, CompareResponse, DivergenceEventIds

log = get_logger("afr.compare")


def compare(task_name: str, req: CompareRequest) -> CompareResponse:
    t0 = time.perf_counter()
    div = memory_router.find_divergence(task_name)

    failed_clip = evidence_compiler.compile_clip(
        div.failure_run, div.divergence_timestamp, req.window_s
    )
    success_clip = evidence_compiler.compile_clip(
        div.success_run, div.divergence_timestamp, req.window_s
    )

    bind_observability(
        task_name=task_name,
        e2e_latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    log.info(
        "compare_done",
        task_name=task_name,
        divergence_timestamp=div.divergence_timestamp,
    )
    return CompareResponse(
        task_name=task_name,
        divergence_timestamp=div.divergence_timestamp,
        failed_clip_url=failed_clip.url,
        success_clip_url=success_clip.url,
        explanation=None,
        divergence_event_ids=DivergenceEventIds(
            success=div.success_event_id,
            failure=div.failure_event_id,
        ),
    )
