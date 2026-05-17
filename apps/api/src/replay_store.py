"""REPLAY_MODE fixture store — the demo's zero-dependency safety net.

`phase-5-reliability.md` mandates that every live feature works in
`REPLAY_MODE=true` against pre-indexed runs under `DEMO_TASK_NAME`. This module
loads `fixtures/demo_login_flow.json` so the full killshot flow
(`/search` → `/compare` → `/explain`) runs with **no VideoDB, no Supabase, no
network**. It is also the fallback when live Supabase Postgres is unreachable
(`ALLOW_FIXTURE_FALLBACK`) so the build stays runnable while DATABASE_URL is
being fixed (see PUNCHLIST.md).

Why a local JSON fixture and not only the Supabase seed: the gate is "the demo
cannot fail". A fixture removes the last shared failure modes (DB creds, network
to Supabase) on the demo path. The Supabase seed (migrations/0002) mirrors this
same data for the live path + eval suite.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import get_settings
from .logging import get_logger

log = get_logger("afr.replay")

_DEFAULT_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "demo_login_flow.json"


@lru_cache(maxsize=1)
def load_fixture() -> dict[str, Any]:
    """Load + cache the replay fixture. Raises if the file is missing/invalid
    (a misconfigured demo safety net must fail loudly at startup, not silently
    at demo time)."""
    settings = get_settings()
    path = Path(settings.REPLAY_FIXTURE_PATH) if settings.REPLAY_FIXTURE_PATH else _DEFAULT_FIXTURE
    data = json.loads(path.read_text())
    # Overlay configurable clip URLs (real exported VideoDB clips slot in here
    # without editing the fixture — see PUNCHLIST.md).
    data["runs"]["success"]["clip_url"] = (
        settings.REPLAY_SUCCESS_CLIP_URL or data["runs"]["success"]["clip_url"]
    )
    data["runs"]["failure"]["clip_url"] = (
        settings.REPLAY_FAILURE_CLIP_URL or data["runs"]["failure"]["clip_url"]
    )
    log.info(
        "replay_fixture_loaded",
        path=str(path),
        task_name=data["task_name"],
        success_events=len(data["runs"]["success"]["events"]),
        failure_events=len(data["runs"]["failure"]["events"]),
    )
    return data


def fixture_task_name() -> str:
    return load_fixture()["task_name"]


def get_run_pair(task_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (success_run, failure_run) dicts for ``task_name`` from the fixture.

    Each run dict carries: id, task_name, run_status, app_version,
    capture_session_id, rtstream_id, started_at, ended_at, clip_url, events[].
    """
    fx = load_fixture()
    if task_name != fx["task_name"]:
        raise KeyError(
            f"replay fixture only has task '{fx['task_name']}', not '{task_name}'"
        )
    return fx["runs"]["success"], fx["runs"]["failure"]


def get_run(run_id: str) -> dict[str, Any] | None:
    """Look a single run up by its fixture id."""
    fx = load_fixture()
    for run in fx["runs"].values():
        if run["id"] == run_id:
            return run
    return None


def get_events(run_id: str) -> list[dict[str, Any]]:
    """Events for a run, ordered by ``t_offset_s`` (the alignment key)."""
    run = get_run(run_id)
    if run is None:
        return []
    return sorted(run["events"], key=lambda e: e["t_offset_s"])


def eval_cases() -> list[dict[str, Any]]:
    return load_fixture().get("eval_cases", [])
