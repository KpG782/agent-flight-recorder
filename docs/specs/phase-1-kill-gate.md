# Phase 1 — Kill-Criterion Gate (HARD STOP)

**Objective:** Prove the core loop works end-to-end before building anything else:
capture → index → natural-language search → timestamped clip.

**Inputs / preconditions:** Phase 0 synthesized; `docs/videodb-cheatsheet.md` complete;
`.env` filled.

**FIRST ACTION (ahead of all build):** Verify the VideoDB **desktop capture client**
runs on macOS Apple Silicon (M4). If unsupported, this invalidates the live-capture
approach — go straight to the pivot decision below; do not build capture code first.

**Parallel agent assignments (Wave 1 — 3 concurrent):**
- `BE-SCAFFOLD`: Turborepo (`apps/web`, `apps/api`, `packages/types`, `turbo.json`);
  FastAPI app + uvicorn; pydantic-settings reading `.env`; Supabase schema migration
  per `data-model.md`; Redis client with **TLS** (`rediss://`, `ssl=True`); VideoDB
  SDK wiring + retry/backoff wrapper (max 3); `structlog` JSON logging; `GET /healthz`.
- `CAPTURE`: `capture_orchestrator.py` + `POST /sessions/start` (returns client token)
  + `POST /sessions/{run_id}/end`, per `api-contracts.md`.
- `INDEX`: wire `index_visuals` with the MASTER prompt and `index_audio` for mic
  transcription; persist scene metadata (`task_id`, `run_status`).

`CAPTURE`/`INDEX` may stub against `api-contracts.md` if scaffold isn't committed yet,
then rebase onto `BE-SCAFFOLD`'s module layout.

**Concrete tasks:** implement `POST /search` (`api-contracts.md`) returning timestamped
shots with `clip_url`; structured logging of the full observability field set.

**Acceptance criteria:** a 30-second real capture session produces indexed events; one
NL query via `POST /search` returns ≥1 timestamped shot with a playable `clip_url`;
the run is logged with `capture_session_id`, `rtstream_id`, `returned_shot_count`,
`e2e_latency_ms`.

**Gate / exit (THE kill-criterion — non-negotiable):**
- **PASS** (30s capture → indexed events → NL search → timestamped clip, with logged
  evidence) → dispatch Wave 2.
- **FAIL** → **STOP. Do not push through.** Contact the user and propose the pivot to
  **Demo Truth Auditor**: upload-based (no live capture) — user uploads two screen
  recordings, same index→search→compare→explain pipeline on uploaded video instead of
  CaptureSession. Await user decision before continuing.

**Risks:** capture client macOS incompatibility (→ pivot); indexing lag 2–5s (acceptable
here, mitigated in demo by pre-indexed data); VideoDB rate limits (backoff, max 3
retries); dense-UI misreads (use a clean demo app — large buttons, clear text).
