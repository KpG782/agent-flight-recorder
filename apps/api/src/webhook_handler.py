"""VideoDB webhook handler (Wave 4 — RELIABILITY).

`POST /webhooks/videodb`: ack 200 fast (<50ms), validate ENVELOPE SHAPE only
(NO HMAC/signature exists upstream — Wave 0 note #3; trust = secret ngrok URL +
`event_id` idempotency), Redis-dedupe on `event_id`, process async, persist to
`events` with the `unique(run_id, event_id)` DB backstop. WS/webhook timestamps
are inconsistent ms/s — normalized to seconds on ingest.

Two payload families (cheatsheet §9): the CaptureSession lifecycle envelope
(`capture_session.*`, no `event_id` — dedupe on
`capture_session_id|event|timestamp`) and the alert/event-trigger payload
(has `event_id`). `capture_session.active` starts the indexing pipelines.
"""

from __future__ import annotations

import hashlib
from typing import Any

from . import indexing, store
from .config import get_settings
from .logging import bind_observability, get_logger
from .ws_broadcaster import broadcast

log = get_logger("afr.webhook")

_IDEM_PREFIX = "afr:webhook:"


def validate_envelope(payload: dict[str, Any]) -> bool:
    """Shape-only validation (no signature exists). Accept either family."""
    if not isinstance(payload, dict):
        return False
    is_lifecycle = "event" in payload and "capture_session_id" in payload
    is_alert = "event_id" in payload and (
        "start_time" in payload or "label" in payload
    )
    return bool(is_lifecycle or is_alert)


def _dedupe_id(payload: dict[str, Any]) -> str:
    if payload.get("event_id"):
        # Documented idempotency recipe: sha256(event_id:timestamp).
        raw = f"{payload['event_id']}:{payload.get('timestamp', '')}"
    else:
        raw = (
            f"{payload.get('capture_session_id')}:"
            f"{payload.get('event')}:{payload.get('timestamp')}"
        )
    return _IDEM_PREFIX + hashlib.sha256(raw.encode()).hexdigest()[:32]


async def is_duplicate(payload: dict[str, Any]) -> bool:
    """Redis `SET key 1 NX EX ttl` — True means already seen (dedupe hit)."""
    try:
        from .clients.redis_client import get_redis

        ttl = get_settings().REDIS_IDEMPOTENCY_TTL_S
        was_set = await get_redis().set(_dedupe_id(payload), "1", nx=True, ex=ttl)
        return not bool(was_set)
    except Exception as exc:  # noqa: BLE001 — Redis down ⇒ DB unique() is the backstop
        log.warning("idempotency_redis_failed", error=str(exc)[:160])
        return False


def _to_seconds(ts: Any) -> float:
    """Normalize a timestamp to seconds. Alert `start_time` is seconds; WS-style
    ms values (> ~10^11) are divided by 1000 (cheatsheet §10)."""
    try:
        v = float(ts)
    except (TypeError, ValueError):
        return 0.0
    return v / 1000.0 if v > 1e11 else v


async def process_event_async(payload: dict[str, Any]) -> None:
    """Run AFTER the fast 200 ack (FastAPI BackgroundTask)."""
    settings = get_settings()
    event = payload.get("event")

    if event and str(event).startswith("capture_session."):
        bind_observability(capture_session_id=payload.get("capture_session_id"))
        if event == "capture_session.active":
            callback = (
                f"{settings.WEBHOOK_BASE_URL}/webhooks/videodb"
                if settings.WEBHOOK_BASE_URL
                else None
            )
            for rt in payload.get("data", {}).get("rtstreams", []):
                try:
                    indexing.start_indexing_for_rtstream(rt, callback)
                except Exception as exc:  # noqa: BLE001
                    log.warning("indexing_start_failed", error=str(exc)[:160])
        log.info("lifecycle_processed", event=event)
        return

    # Alert / scene-event payload → persist as an event row + WS fanout.
    cap_id = payload.get("capture_session_id")
    run = None
    if cap_id:
        # Correlate scene → run via capture_session_id (Wave 0 note #2).
        try:
            from .clients.supabase_client import get_supabase

            res = (
                get_supabase()
                .table("runs")
                .select("*")
                .eq("capture_session_id", cap_id)
                .limit(1)
                .execute()
            )
            run = res.data[0] if res.data else None
        except Exception:  # noqa: BLE001 — correlation best-effort
            run = None
    if run is None:
        log.warning("event_uncorrelated", capture_session_id=cap_id)
        return

    t_offset = _to_seconds(payload.get("start_time"))
    started = run.get("started_at")
    row = {
        "event_id": payload["event_id"],
        "t_offset_s": t_offset,
        "channel": "display",
        "description": payload.get("explanation") or payload.get("label") or "",
        "template_tag": payload.get("label")
        if payload.get("label")
        in ("unexpected_modal", "stuck_spinner", "auth_failure")
        else None,
        "raw": payload,
    }
    inserted = store.upsert_event(run["id"], row)
    log.info("event_persisted", run_id=run["id"], inserted=inserted)
    await broadcast(
        run["id"],
        {
            "type": "event",
            "run_id": run["id"],
            "t_offset_s": t_offset,
            "description": row["description"],
            "template_tag": row["template_tag"],
        },
    )
