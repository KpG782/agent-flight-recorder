"""Capture orchestration (Wave 1).

Backs `POST /sessions/start` + `POST /sessions/{run_id}/end`
(api-contracts.md). Per Wave 0 note #2 run metadata lives on
`CaptureSession(metadata=...)`; scene→run correlation is in Supabase.

REPLAY_MODE short-circuits live capture entirely (phase-5-reliability.md):
`/sessions/start` returns a synthetic session/token so a capture client *could*
be pointed at the demo without touching VideoDB. The live path is implemented
per docs/videodb-cheatsheet.md §2 but is not exercised by the demo (the
kill-gate live-capture step is deferred to PUNCHLIST.md).

Spec: docs/specs/phase-1-kill-gate.md
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from . import store
from .clients import videodb_client
from .config import get_settings
from .logging import bind_observability, get_logger
from .schemas import (
    SessionEndRequest,
    SessionEndResponse,
    SessionStartRequest,
    SessionStartResponse,
)

log = get_logger("afr.capture")

_CLIENT_TOKEN_TTL_S = 600  # short-lived; never ship the API key (cheatsheet §2b)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def start_session(req: SessionStartRequest) -> SessionStartResponse:
    """Create a run + (live) a VideoDB CaptureSession with run-scoped metadata,
    then mint a short-lived client token."""
    settings = get_settings()
    run = store.create_run(req.task_name, req.run_status, req.app_version)
    bind_observability(task_name=req.task_name, run_id=run["id"])

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_CLIENT_TOKEN_TTL_S)

    if settings.REPLAY_MODE:
        # Why synthetic: replay must not require VideoDB reachability.
        log.info("session_start_replay", run_id=run["id"], task_name=req.task_name)
        return SessionStartResponse(
            run_id=run["id"],
            capture_session_id=f"cap-replay-{run['id'][:8]}",
            client_token="replay-no-token",
            expires_at=_iso(expires_at),
        )

    conn = videodb_client.get_connection()
    callback_url = (
        f"{settings.WEBHOOK_BASE_URL}/webhooks/videodb"
        if settings.WEBHOOK_BASE_URL
        else None
    )
    cap = videodb_client.with_retry(
        conn.create_capture_session,
        end_user_id=run["id"],
        collection_id="default",
        callback_url=callback_url,
        metadata={
            "task_name": req.task_name,
            "run_id": run["id"],
            "run_status": req.run_status,
            "app_version": req.app_version,
        },
    )
    store.set_run_capture(run["id"], cap.id)
    token = videodb_client.with_retry(
        conn.generate_client_token, expires_in=_CLIENT_TOKEN_TTL_S
    )
    bind_observability(capture_session_id=cap.id)
    log.info("session_started", run_id=run["id"], capture_session_id=cap.id)
    return SessionStartResponse(
        run_id=run["id"],
        capture_session_id=cap.id,
        client_token=token,
        expires_at=_iso(expires_at),
    )


def end_session(run_id: str, req: SessionEndRequest) -> SessionEndResponse:
    """Finalize a run. Live: export the display RTStream so it is replayable
    later (primitive #3). Replay: just close out the fixture run."""
    settings = get_settings()
    t0 = time.perf_counter()
    run = store.get_run(run_id)
    if run is None:
        raise LookupError(f"run {run_id} not found")
    bind_observability(run_id=run_id, task_name=run.get("task_name"))

    rtstream_id = run.get("rtstream_id")
    if not settings.REPLAY_MODE and run.get("capture_session_id"):
        try:
            conn = videodb_client.get_connection()
            from videodb import RTStreamChannelType

            cap = videodb_client.with_retry(
                conn.get_capture_session, run["capture_session_id"]
            )
            screens = cap.get_rtstream(RTStreamChannelType.screen)
            if screens:
                rts = screens[0]
                rtstream_id = rts.id
                videodb_client.with_retry(
                    rts.export, name=f"{run.get('task_name')} - {req.run_status} run"
                )
        except Exception as exc:  # noqa: BLE001 — export is best-effort
            log.warning("rtstream_export_failed", run_id=run_id, error=str(exc)[:160])

    ended = store.end_run(run_id, req.run_status, rtstream_id)
    bind_observability(
        rtstream_id=rtstream_id, e2e_latency_ms=int((time.perf_counter() - t0) * 1000)
    )
    log.info("session_ended", run_id=run_id, run_status=req.run_status)
    return SessionEndResponse(
        run_id=run_id,
        rtstream_id=rtstream_id or "",
        ended_at=ended.get("ended_at") or _iso(datetime.now(timezone.utc)),
    )
