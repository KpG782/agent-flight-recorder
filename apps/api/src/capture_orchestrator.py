"""Capture orchestration — OWNED BY THE `CAPTURE` AGENT (Wave 1).

Responsibility (architecture.md): create a VideoDB CaptureSession with
run-scoped metadata, mint a short-lived client token, wire display+mic
channels, and back `POST /sessions/start` + `POST /sessions/{run_id}/end`
(api-contracts.md). Per Wave 0 note #2, run metadata lives on
`CaptureSession(metadata=...)`; scene→run correlation is in Supabase.

Spec: docs/specs/phase-1-kill-gate.md
TODO(CAPTURE): implement; this scaffold intentionally contains no logic.
"""

from __future__ import annotations
