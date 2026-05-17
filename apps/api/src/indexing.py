"""Indexing pipeline wiring (Wave 1 — INDEX).

On `capture_session.active` the webhook handler hands each RTStream here:
- video channel → `index_visuals` with the MASTER scene prompt at the 1 frame/5s
  cost cadence (CAPTURE_FRAME_INTERVAL_S), plus the 3 reusable event-template
  alerts (primitive #6).
- audio channel → `start_transcript` + `index_audio` (primitive #1, mic).

Live VideoDB only — REPLAY serves pre-indexed events from the fixture, so this
module is never called in replay. Signatures per docs/videodb-cheatsheet.md
§4/§5/§11.

Spec: docs/specs/phase-1-kill-gate.md
"""

from __future__ import annotations

from typing import Any

from .clients import videodb_client
from .config import get_settings
from .logging import get_logger

log = get_logger("afr.index")

# The MASTER visual-scene prompt (specific, UI-forensic).
_VISUAL_PROMPT = (
    "Identify visible UI elements, button clicks, page transitions, error "
    "states, modal dialogs, form submissions, and authentication screens. Be "
    "specific about what app or page is shown and any text visible. Note login "
    "fields, typed values, and any validation or error messaging."
)
_AUDIO_PROMPT = (
    "Summarize what the user or agent said and any spoken errors or commands."
)

# Reusable event templates (primitive #6) — created once per process, reused
# across every run/stream as alerts.
_TEMPLATE_DEFS = (
    ("unexpected_modal", "An unexpected modal dialog or popup appears over the app UI"),
    ("stuck_spinner", "A loading spinner or progress indicator stays visible without resolving"),
    ("auth_failure", "An authentication or login failure / invalid credentials error is shown"),
)
_event_template_ids: dict[str, str] | None = None


def ensure_event_templates() -> dict[str, str]:
    """Create (idempotently) the 3 reusable event templates; cache their ids.

    Reuses an existing template if one with the same label already exists so
    re-runs don't pile up duplicates.
    """
    global _event_template_ids
    if _event_template_ids is not None:
        return _event_template_ids
    conn = videodb_client.get_connection()
    existing = {}
    try:
        for ev in videodb_client.with_retry(conn.list_events) or []:
            label = ev.get("label")
            if label:
                existing[label] = ev.get("event_id") or ev.get("id")
    except Exception as exc:  # noqa: BLE001 — listing is best-effort
        log.warning("list_events_failed", error=str(exc)[:160])
    ids: dict[str, str] = {}
    for label, prompt in _TEMPLATE_DEFS:
        ids[label] = existing.get(label) or videodb_client.with_retry(
            conn.create_event, event_prompt=prompt, label=label
        )
    _event_template_ids = ids
    log.info("event_templates_ready", labels=list(ids.keys()))
    return ids


def start_indexing_for_rtstream(rtstream_desc: dict[str, Any], callback_url: str | None) -> None:
    """Start the right index pipeline for one RTStream from a webhook
    `capture_session.active` `data.rtstreams[]` entry.

    `rtstream_desc` shape (cheatsheet §9a):
      { "rtstream_id": "rts-..", "name": "display:1", "media_types": ["video"] }
    """
    if get_settings().REPLAY_MODE:
        return
    conn = videodb_client.get_connection()
    coll = conn.get_collection("default")
    rts = videodb_client.with_retry(coll.get_rtstream, rtstream_desc["rtstream_id"])
    media = rtstream_desc.get("media_types", [])
    interval = get_settings().CAPTURE_FRAME_INTERVAL_S

    if "video" in media:
        scene_index = videodb_client.with_retry(
            rts.index_visuals,
            prompt=_VISUAL_PROMPT,
            # 1 frame / interval s — cost rule (PLAN.md / README cost model).
            batch_config={"type": "time", "value": interval, "frame_count": 1},
            name="ui_events",
        )
        callback = callback_url
        if callback:
            for label, event_id in ensure_event_templates().items():
                try:
                    videodb_client.with_retry(
                        scene_index.create_alert,
                        event_id=event_id,
                        callback_url=callback,
                    )
                except Exception as exc:  # noqa: BLE001 — alert wiring best-effort
                    log.warning(
                        "create_alert_failed", label=label, error=str(exc)[:160]
                    )
        log.info(
            "index_visuals_started",
            rtstream_id=rtstream_desc["rtstream_id"],
            frame_interval_s=interval,
        )

    if "audio" in media:
        videodb_client.with_retry(rts.start_transcript)
        videodb_client.with_retry(
            rts.index_audio,
            prompt=_AUDIO_PROMPT,
            batch_config={"type": "sentence", "value": 1},
            name="audio",
        )
        log.info("index_audio_started", rtstream_id=rtstream_desc["rtstream_id"])
