"""Memory routing / divergence detection — OWNED BY THE `MEMORY` AGENT.

Responsibility (architecture.md): per `task_name`, fetch both runs' event
streams, embed descriptions, compute the first semantic divergence point.
Backs `POST /tasks/{task_name}/compare` (api-contracts.md, Phase 2). Search is
RTStream semantic search (`rts.search`) — collection keyword search raises
`NotImplementedError` (videodb-cheatsheet §7).

Spec: docs/specs/phase-2-comparison.md
TODO(MEMORY): implement; this scaffold intentionally contains no logic.
"""

from __future__ import annotations
