"""WebSocket live fanout — OWNED BY THE `RELIABILITY` AGENT.

Responsibility (architecture.md / api-contracts.md): fan out live events to
connected WebSocket clients for the active run. Best-effort / at-most-once —
truth lives in the webhook path (dual-delivery rationale). Backs
`WS /ws?run_id=...`. Upstream WS uses `ws.receive()` (not `ws.stream()`) and
event ts are in ms — normalize to seconds (videodb-cheatsheet §10).

Spec: docs/specs/phase-3-ui.md / phase-5-reliability.md
TODO(RELIABILITY): implement; this scaffold intentionally contains no logic.
"""

from __future__ import annotations
