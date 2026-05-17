"""Natural-language search over a run's indexed events (Phase-1 kill-criterion).

Backs `POST /search` (api-contracts.md). This endpoint passing end-to-end *is*
the kill-criterion gate.

- LIVE: `RTStream.search` (semantic) on the run's display stream — collection
  keyword search raises NotImplementedError (cheatsheet §7).
- REPLAY / fixture: rank the run's pre-indexed events against the query with the
  stdlib similarity scorer; the clip is the run's stream seeked to the shot.
"""

from __future__ import annotations

import time

from . import store
from .clients import videodb_client
from .config import get_settings
from .logging import bind_observability, get_logger
from .schemas import SearchRequest, SearchResponse, Shot
from .similarity import score as sim_score

log = get_logger("afr.search")


def search(req: SearchRequest) -> SearchResponse:
    settings = get_settings()
    t0 = time.perf_counter()
    bind_observability(run_id=req.run_id, query_text=req.query)

    run = store.get_run(req.run_id)
    if run is None:
        raise LookupError(f"run {req.run_id} not found")

    # No real VideoDB stream (replay or seeded demo run) ⇒ rank the stored
    # events; only hit live RTStream search for a genuine captured stream.
    if settings.REPLAY_MODE or store.is_synthetic_run(run):
        shots = _search_fixture(run, req)
    else:
        shots = _search_live(run, req)

    e2e = int((time.perf_counter() - t0) * 1000)
    bind_observability(
        returned_shot_count=len(shots),
        relevance_scores=[s.score for s in shots],
        e2e_latency_ms=e2e,
    )
    log.info(
        "search_done",
        run_id=req.run_id,
        returned_shot_count=len(shots),
        e2e_latency_ms=e2e,
    )
    return SearchResponse(
        shots=shots, returned_shot_count=len(shots), e2e_latency_ms=e2e
    )


def _search_fixture(run: dict, req: SearchRequest) -> list[Shot]:
    interval = get_settings().CAPTURE_FRAME_INTERVAL_S
    events = run.get("events") or store.get_events(req.run_id)
    clip_url = store.resolve_clip_url(run)
    ranked = sorted(
        ((sim_score(req.query, e["description"]), e) for e in events),
        key=lambda x: x[0],
        reverse=True,
    )
    shots: list[Shot] = []
    for s, e in ranked[: max(1, req.k)]:
        t = float(e["t_offset_s"])
        shots.append(
            Shot(
                shot_id=e["event_id"],
                t_start_s=t,
                t_end_s=t + interval,
                score=float(s),
                description=e["description"],
                clip_url=clip_url,
            )
        )
    return shots


def _search_live(run: dict, req: SearchRequest) -> list[Shot]:
    rtstream_id = run.get("rtstream_id")
    if not rtstream_id:
        raise LookupError(f"run {req.run_id} has no rtstream_id (not indexed yet)")
    conn = videodb_client.get_connection()
    coll = conn.get_collection("default")
    rts = videodb_client.with_retry(coll.get_rtstream, rtstream_id)
    result = videodb_client.with_retry(
        rts.search, query=req.query, result_threshold=req.k, score_threshold=0.2
    )
    shots: list[Shot] = []
    for sh in result.get_shots():
        start = float(sh.start)
        end = float(sh.end)
        # Bound a playable clip around the shot (cheatsheet §8b — no compile()
        # on RTStreamSearchResult; generate_stream with an explicit window).
        clip_url = videodb_client.with_retry(
            rts.generate_stream, start=int(start), end=int(end)
        )
        shots.append(
            Shot(
                shot_id=f"{sh.scene_index_id}:{int(start)}",
                t_start_s=start,
                t_end_s=end,
                score=float(getattr(sh, "search_score", 0.0) or 0.0),
                description=sh.text or "",
                clip_url=clip_url,
            )
        )
    return shots
