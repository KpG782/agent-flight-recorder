"""Evidence clip compilation — OWNED BY THE `EVIDENCE` AGENT.

Responsibility (architecture.md): given the divergence timestamp, build a
playable evidence clip per run. There is no `compile()` on
`RTStreamSearchResult` — bound a ±window around the divergence Unix timestamp
and call `rts.generate_stream(start-W, end+W)` per run (videodb-cheatsheet §8b).
Satisfies VideoDB primitive #4.

Spec: docs/specs/phase-2-comparison.md
TODO(EVIDENCE): implement; this scaffold intentionally contains no logic.
"""

from __future__ import annotations
