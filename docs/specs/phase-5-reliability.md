# Phase 5 — Reliability + Fallback

**Objective:** Make the durable path bulletproof and guarantee the demo cannot fail
via a fully pre-indexed replay mode.

**Inputs / preconditions:** Phases 1–4 working; `webhook_handler.py` stub from
Phase 1 scaffold; `WEBHOOK_BASE_URL` (ngrok) reachable.

**Parallel agent assignments (Wave 4 — `RELIABILITY` runs concurrently with `CLAUDE`):**
- `RELIABILITY`:
  1. `webhook_handler.py`: `POST /webhooks/videodb` acks `200` in **<50ms**; verify
     signature; Redis idempotency key on `event_id` (`REDIS_IDEMPOTENCY_TTL_S`); push
     to async processing; persist with `unique(run_id, event_id)` DB backstop; log
     `webhook_dedupe_hit`.
  2. WebSocket fanout (`ws_broadcaster.py`): at-most-once is acceptable (truth is in
     the webhook path).
  3. **REPLAY_MODE:** `REPLAY_MODE=true` bypasses live capture entirely and serves two
     pre-recorded, pre-indexed runs stored under `DEMO_TASK_NAME=demo_login_flow`
     (success run vs. failure run where the password field is mistyped). All endpoints
     (`/compare`, `/explain`, video) work against these without touching VideoDB live.

**Concrete tasks:** record the two scripted real capture sessions of "log into a demo
SaaS dashboard" (clean app: large buttons, clear text); pre-index both; store run rows
+ events; wire the `REPLAY_MODE` switch into `capture_orchestrator`/`memory_router`.

**Acceptance criteria:** webhook handler acks <50ms and dedupes duplicate `event_id`;
with `REPLAY_MODE=true` and no network to VideoDB, the full killshot flow
(`/compare` → synced scrub → streamed explanation) works.

**Gate / exit:** **REPLAY_MODE demo runs green 3× consecutively** (release-blocking) →
dispatch Wave 5.

**Risks:** capture permission prompt mid-demo (grant all perms, restart, test 3×);
network drop during live demo (REPLAY_MODE is the answer — verified 3×); webhook
duplicates (Redis + DB unique backstop); ngrok URL churn (re-register
`WEBHOOK_BASE_URL` before recording).
