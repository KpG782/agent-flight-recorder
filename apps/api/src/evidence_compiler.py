"""Evidence clip compilation (Wave 2 — EVIDENCE).

Given the divergence timestamp ± `window_s`, produce a playable clip URL per
run. There is no `compile()` on `RTStreamSearchResult` — bound a ±window around
the divergence Unix timestamp and call `rts.generate_stream(start-W, end+W)`
(cheatsheet §8b). Satisfies VideoDB primitive #4.

REPLAY / fixture: the run's pre-exported clip is the whole short run; the UI
seeks both `<video>` elements to `divergence_timestamp` (the window is advisory
metadata only — there is no live stream to re-bound).

Spec: docs/specs/phase-2-comparison.md
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from . import store
from .clients import videodb_client
from .config import get_settings
from .logging import get_logger

log = get_logger("afr.evidence")


@dataclass
class Clip:
    url: str
    window_start_s: float
    window_end_s: float


def _window(divergence_ts: float, window_s: int, run_started: float = 0.0) -> tuple[float, float]:
    # Clamp to the run start (cheatsheet/spec risk: off-by-window bounds).
    start = max(run_started, divergence_ts - window_s)
    return start, divergence_ts + window_s


def compile_clip(run: dict, divergence_ts: float, window_s: int) -> Clip:
    """Build one run's evidence clip around ``divergence_ts``."""
    settings = get_settings()
    t0 = time.perf_counter()
    use_fixture = settings.REPLAY_MODE or "events" in run or store._use_fixture()  # noqa: SLF001
    w_start, w_end = _window(divergence_ts, window_s)

    if use_fixture:
        clip = Clip(url=run["clip_url"], window_start_s=w_start, window_end_s=w_end)
    else:
        rtstream_id = run.get("rtstream_id")
        if not rtstream_id:
            raise LookupError(f"run {run.get('id')} has no rtstream_id")
        conn = videodb_client.get_connection()
        coll = conn.get_collection("default")
        rts = videodb_client.with_retry(coll.get_rtstream, rtstream_id)
        # RTStream timestamps are Unix epoch seconds (cheatsheet §3/§8b). The
        # divergence offset is run-relative; the live path adds it to the run's
        # capture epoch start, persisted on the run row.
        epoch0 = float(run.get("capture_epoch_s") or 0.0)
        url = videodb_client.with_retry(
            rts.generate_stream,
            start=int(epoch0 + w_start),
            end=int(epoch0 + w_end),
            player_config={"title": f"divergence ±{window_s}s"},
        )
        clip = Clip(url=url, window_start_s=w_start, window_end_s=w_end)

    log.info(
        "clip_compiled",
        run_id=run.get("id"),
        run_status=run.get("run_status"),
        compile_job_duration_ms=int((time.perf_counter() - t0) * 1000),
        window=[w_start, w_end],
    )
    return clip
