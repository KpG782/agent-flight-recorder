"""VideoDB webhook handler — OWNED BY THE `RELIABILITY` AGENT.

Responsibility (architecture.md / api-contracts.md): ack 200 in <50ms, validate
ENVELOPE SHAPE only (NO HMAC/signature exists in the VideoDB SDK or docs — Wave
0 note #3; trust boundary is the secret ngrok URL + `event_id` idempotency),
Redis dedupe on `event_id`, async process, persist to `events` with the
`unique(run_id, event_id)` backstop. Normalize event timestamps ms→s on ingest.

Spec: docs/specs/phase-5-reliability.md
TODO(RELIABILITY): implement; this scaffold intentionally contains no logic.
NOTE: do NOT add signature verification — none exists upstream.
"""

from __future__ import annotations
