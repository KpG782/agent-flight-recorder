"""WebSocket live fanout (Wave 4 — RELIABILITY).

`WS /ws?run_id=...` — best-effort / at-most-once. Truth lives in the webhook
path (the dual-delivery rationale: webhooks are durable at-least-once; WS is
disposable live UX). Server→client frames mirror `WsEventFrame`.

In REPLAY there is no live capture, so on connect for the demo task the failure
run's pre-indexed events are gently replayed (with small delays) so the UI
event rail populates exactly as it would live — without VideoDB.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from . import replay_store, store
from .config import get_settings
from .logging import get_logger

log = get_logger("afr.ws")

_clients: dict[str, set[WebSocket]] = defaultdict(set)


async def register(run_id: str, ws: WebSocket) -> None:
    await ws.accept()
    _clients[run_id].add(ws)
    log.info("ws_connected", run_id=run_id, clients=len(_clients[run_id]))


def unregister(run_id: str, ws: WebSocket) -> None:
    _clients[run_id].discard(ws)
    if not _clients[run_id]:
        _clients.pop(run_id, None)


async def broadcast(run_id: str, frame: dict[str, Any]) -> None:
    """Push a frame to every client on ``run_id``. Dead sockets are dropped
    silently (at-most-once — never block the truth path on a slow client)."""
    dead = []
    for ws in list(_clients.get(run_id, ())):
        try:
            await ws.send_json(frame)
        except Exception:  # noqa: BLE001
            dead.append(ws)
    for ws in dead:
        unregister(run_id, ws)


async def replay_feed(run_id: str) -> None:
    """REPLAY-only: stream the fixture failure run's events as a live-ish feed
    so the event rail looks identical to a live capture, with no VideoDB."""
    if not get_settings().REPLAY_MODE:
        return
    try:
        _, failure = replay_store.get_run_pair(replay_store.fixture_task_name())
    except Exception:  # noqa: BLE001
        return
    # Broadcast back on the SAME key the client connected with (registration
    # key), not the run's own id — otherwise the fanout misses the socket.
    events = store.get_events(failure["id"])
    log.info("replay_feed_start", run_id=run_id, events=len(events))
    for e in events:
        await asyncio.sleep(0.4)  # gentle cadence; not wall-clock accurate
        await broadcast(
            run_id,
            {
                "type": "event",
                "run_id": run_id,
                "t_offset_s": float(e["t_offset_s"]),
                "description": e["description"],
                "template_tag": e.get("template_tag"),
            },
        )
