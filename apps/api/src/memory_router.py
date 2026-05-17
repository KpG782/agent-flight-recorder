"""Memory routing / first-semantic-divergence (Wave 2 — MEMORY).

Given `task_name`, fetch the success + failure runs' event streams (Supabase or
fixture via `store`), align them by `t_offset_s`, and find the **first** aligned
scene pair whose semantic similarity drops below
`MEMORY_DIVERGENCE_THRESHOLD` — that is where the failed run first diverged.

Embedding choice & trade-off documented in `similarity.py` (stdlib lexical-
semantic scorer; no vector-provider dependency, deterministic for the demo
corpus). Emits `divergence_timestamp` + `divergence_event_ids`.

Spec: docs/specs/phase-2-comparison.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import store
from .config import get_settings
from .logging import bind_observability, get_logger
from .similarity import divergence_similarity

log = get_logger("afr.memory")


@dataclass
class Divergence:
    divergence_timestamp: float
    success_event_id: str
    failure_event_id: str
    success_run: dict[str, Any]
    failure_run: dict[str, Any]
    similarity_at_divergence: float


def _by_offset(events: list[dict[str, Any]]) -> dict[float, dict[str, Any]]:
    return {float(e["t_offset_s"]): e for e in events}


def find_divergence(task_name: str) -> Divergence:
    """Compute the first semantic divergence between the task's success and
    failure runs.

    Alignment is by shared `t_offset_s` (both runs share the 1-frame/interval
    cadence). The first offset whose paired descriptions fall below the
    similarity threshold is the divergence; if sequences never fall below it
    but differ in length, the first unmatched offset is the divergence.
    """
    settings = get_settings()
    success, failure = store.get_run_pair(task_name)
    s_events = success.get("events") or store.get_events(success["id"])
    f_events = failure.get("events") or store.get_events(failure["id"])
    bind_observability(task_name=task_name, run_id=failure["id"])

    s_map = _by_offset(s_events)
    f_map = _by_offset(f_events)
    offsets = sorted(set(s_map) | set(f_map))
    threshold = settings.MEMORY_DIVERGENCE_THRESHOLD

    for off in offsets:
        s_ev = s_map.get(off)
        f_ev = f_map.get(off)
        if s_ev is None or f_ev is None:
            # One run has a scene the other doesn't at this offset → divergence.
            present = f_ev or s_ev
            div = Divergence(
                divergence_timestamp=off,
                success_event_id=(s_ev or present)["event_id"],
                failure_event_id=(f_ev or present)["event_id"],
                success_run=success,
                failure_run=failure,
                similarity_at_divergence=0.0,
            )
            break
        sim = divergence_similarity(s_ev["description"], f_ev["description"])
        if sim < threshold:
            div = Divergence(
                divergence_timestamp=off,
                success_event_id=s_ev["event_id"],
                failure_event_id=f_ev["event_id"],
                success_run=success,
                failure_run=failure,
                similarity_at_divergence=sim,
            )
            break
    else:
        # No semantic divergence found — degrade gracefully to the failure
        # run's last scene rather than 500-ing the killshot.
        last_off = offsets[-1]
        s_ev = s_map.get(last_off) or list(s_map.values())[-1]
        f_ev = f_map.get(last_off) or list(f_map.values())[-1]
        div = Divergence(
            divergence_timestamp=last_off,
            success_event_id=s_ev["event_id"],
            failure_event_id=f_ev["event_id"],
            success_run=success,
            failure_run=failure,
            similarity_at_divergence=divergence_similarity(
                s_ev["description"], f_ev["description"]
            ),
        )
        log.warning("no_divergence_below_threshold", task_name=task_name)

    log.info(
        "divergence_found",
        task_name=task_name,
        divergence_timestamp=div.divergence_timestamp,
        similarity=div.similarity_at_divergence,
        success_event_id=div.success_event_id,
        failure_event_id=div.failure_event_id,
    )
    return div


def event_sequences(task_name: str) -> tuple[list[dict], list[dict], Divergence]:
    """Helper for the CLAUDE explanation layer: the two ordered event lists +
    the computed divergence (so the prompt is built from provided events only)."""
    div = find_divergence(task_name)
    s_events = div.success_run.get("events") or store.get_events(div.success_run["id"])
    f_events = div.failure_run.get("events") or store.get_events(div.failure_run["id"])
    s_events = sorted(s_events, key=lambda e: e["t_offset_s"])
    f_events = sorted(f_events, key=lambda e: e["t_offset_s"])
    return s_events, f_events, div
