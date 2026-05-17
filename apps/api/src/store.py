"""Metadata store dispatcher — Supabase (live) with fixture/in-memory fallback.

Hard rule (architecture.md): Supabase holds run metadata / events / eval
results ONLY; media + scene index live in VideoDB. This module is the single
read/write surface for `runs` and `events` so every endpoint behaves
identically whether it is talking to live Supabase or the REPLAY fixture.

Resolution order per call:
1. `REPLAY_MODE=true`  → always the fixture (demo safety net).
2. else Supabase REST (service-role) if the tables are reachable.
3. else, if `ALLOW_FIXTURE_FALLBACK`, the fixture (keeps the build runnable
   while DATABASE_URL is being fixed — see PUNCHLIST.md), plus a small
   in-process map for live-capture writes so `/sessions/*` stay coherent.

We use the supabase-py REST client (not asyncpg) for runs/events because the
DIRECT Postgres endpoint currently rejects auth; REST (PostgREST + JWT) uses a
different trust path and works once the schema exists (migrations/0001+0002).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from . import replay_store
from .config import get_settings
from .logging import get_logger

log = get_logger("afr.store")

# In-process runs created when no DB is reachable (live-capture path only;
# REPLAY never writes). Not durable — durability needs the Supabase fix.
_mem_runs: dict[str, dict[str, Any]] = {}
_supabase_ok: bool | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_replay() -> bool:
    return get_settings().REPLAY_MODE


def supabase_available() -> bool:
    """Cheap one-shot probe: can we read `runs` over REST? Cached per process."""
    global _supabase_ok
    if _supabase_ok is not None:
        return _supabase_ok
    try:
        from .clients.supabase_client import get_supabase

        get_supabase().table("runs").select("id").limit(1).execute()
        _supabase_ok = True
    except Exception as exc:  # noqa: BLE001 — any failure ⇒ use fallback
        log.warning("supabase_unavailable_using_fixture", error=str(exc)[:160])
        _supabase_ok = False
    return _supabase_ok


def _use_fixture() -> bool:
    if is_replay():
        return True
    if supabase_available():
        return False
    if get_settings().ALLOW_FIXTURE_FALLBACK:
        return True
    raise RuntimeError("Supabase unavailable and ALLOW_FIXTURE_FALLBACK is off")


# ── runs ──────────────────────────────────────────────────────────────────
def create_run(task_name: str, run_status: str, app_version: str | None) -> dict[str, Any]:
    run = {
        "id": str(uuid.uuid4()),
        "task_name": task_name,
        "run_status": run_status,
        "app_version": app_version,
        "capture_session_id": None,
        "rtstream_id": None,
        "started_at": _now_iso(),
        "ended_at": None,
    }
    if _use_fixture():
        _mem_runs[run["id"]] = run
        return run
    from .clients.supabase_client import get_supabase

    get_supabase().table("runs").insert(run).execute()
    return run


def set_run_capture(run_id: str, capture_session_id: str) -> None:
    if run_id in _mem_runs:
        _mem_runs[run_id]["capture_session_id"] = capture_session_id
        return
    if not _use_fixture():
        from .clients.supabase_client import get_supabase

        get_supabase().table("runs").update(
            {"capture_session_id": capture_session_id}
        ).eq("id", run_id).execute()


def end_run(run_id: str, run_status: str, rtstream_id: str | None) -> dict[str, Any]:
    patch = {
        "run_status": run_status,
        "rtstream_id": rtstream_id,
        "ended_at": _now_iso(),
    }
    if run_id in _mem_runs:
        _mem_runs[run_id].update(patch)
        return _mem_runs[run_id]
    if _use_fixture():
        run = replay_store.get_run(run_id) or {}
        return {**run, **patch, "id": run_id}
    from .clients.supabase_client import get_supabase

    get_supabase().table("runs").update(patch).eq("id", run_id).execute()
    return {**patch, "id": run_id}


def get_run(run_id: str) -> dict[str, Any] | None:
    if run_id in _mem_runs:
        return _mem_runs[run_id]
    if _use_fixture():
        return replay_store.get_run(run_id)
    from .clients.supabase_client import get_supabase

    res = get_supabase().table("runs").select("*").eq("id", run_id).limit(1).execute()
    return res.data[0] if res.data else None


def get_run_pair(task_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (success_run, failure_run) for ``task_name``, each with ``events``.

    Picks the most recent run per status so re-captures don't break the demo.
    """
    if _use_fixture():
        return replay_store.get_run_pair(task_name)
    from .clients.supabase_client import get_supabase

    sb = get_supabase()
    runs = (
        sb.table("runs")
        .select("*")
        .eq("task_name", task_name)
        .order("started_at", desc=True)
        .execute()
        .data
    )
    success = next((r for r in runs if r["run_status"] == "success"), None)
    failure = next((r for r in runs if r["run_status"] == "failure"), None)
    if not success or not failure:
        raise LookupError(
            f"task '{task_name}' needs one success and one failure run "
            f"(have success={bool(success)}, failure={bool(failure)})"
        )
    for r in (success, failure):
        r["events"] = get_events(r["id"])
    return success, failure


def is_synthetic_run(run: dict[str, Any]) -> bool:
    """True when a run has no real VideoDB media to stream — i.e. it is the
    seeded/fixture demo data (rtstream id absent or a `rts-replay-*` stub).
    Such runs must be served the configured placeholder clips, not a live
    `generate_stream` call (there is nothing to generate)."""
    rid = (run or {}).get("rtstream_id") or ""
    return not rid or str(rid).startswith("rts-replay")


def resolve_clip_url(run: dict[str, Any]) -> str:
    """Clip URL for a run regardless of backing store. Fixture rows carry
    `clip_url`; Supabase rows don't (live clips come from VideoDB) — for the
    seeded demo runs fall back to the configured placeholder by run_status."""
    if run.get("clip_url"):
        return run["clip_url"]
    s = get_settings()
    return (
        s.REPLAY_SUCCESS_CLIP_URL
        if run.get("run_status") == "success"
        else s.REPLAY_FAILURE_CLIP_URL
    )


def get_events(run_id: str) -> list[dict[str, Any]]:
    if _use_fixture():
        return replay_store.get_events(run_id)
    from .clients.supabase_client import get_supabase

    res = (
        get_supabase()
        .table("events")
        .select("*")
        .eq("run_id", run_id)
        .order("t_offset_s")
        .execute()
    )
    return res.data or []


# ── events (webhook ingest backstop) ──────────────────────────────────────
def upsert_event(run_id: str, event: dict[str, Any]) -> bool:
    """Insert one event, relying on the `unique(run_id, event_id)` DB backstop
    for idempotency. Returns False if it was a duplicate (or fixture mode)."""
    if _use_fixture():
        return False  # replay is read-only; Redis dedupe still logged upstream
    from .clients.supabase_client import get_supabase

    try:
        get_supabase().table("events").insert({"run_id": run_id, **event}).execute()
        return True
    except Exception as exc:  # noqa: BLE001 — unique-violation ⇒ duplicate
        if "duplicate" in str(exc).lower() or "23505" in str(exc):
            return False
        raise
