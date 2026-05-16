# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repo currently contains only `MASTER.md` — the full mission briefing for **Agent Flight Recorder**, a VideoDB "Eyes and Ears" hackathon build. No code, build system, or git history exists yet. `MASTER.md` is the authoritative spec; read it in full before starting implementation. This file is the distilled operating guide.

**Hard deadline:** May 18, 2026, 12:30 PM Manila time. Solo build. Treat time as the binding constraint — phases below are gated, not aspirational.

## What is being built

A forensic tool that captures agent/app runs as video memory via VideoDB, then answers "where did the failed run first diverge from the successful one?" The killshot demo: user types that question → two synced `<video>` panes scrub to the divergence timestamp → red timeline marker → Claude-streamed plain-English explanation.

## Fixed stack (no debate — ask before deviating)

- **Backend:** FastAPI (Python 3.11+), uvicorn — `apps/api`
- **Frontend:** Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui — `apps/web`
- **Monorepo:** Turborepo, shared `packages/types`
- **DB:** Supabase (Postgres) — run metadata, labels, eval results ONLY
- **Cache/Queue:** Redis — idempotency keys, hot event fanout, demo cache
- **Media memory:** VideoDB — source of truth for media; never duplicate media into Supabase
- **LLM:** Claude API (Sonnet) — used ONLY for the final natural-language divergence explanation, never for retrieval orchestration

## Architecture

Capture client → FastAPI → VideoDB SDK (with Supabase + Redis side stores) → dual delivery to Next.js: WebSocket for live UX, webhooks for durable at-least-once truth. The webhook path is the state of truth; WebSocket is best-effort live display.

Core `apps/api/src/` modules: `capture_orchestrator.py` (CaptureSession + token), `memory_router.py` (fetch run event streams, embed, find first semantic divergence), `evidence_compiler.py` (VideoDB compile-search-results → playable clip URLs), `incident_evaluator.py` (eval suite), `webhook_handler.py` (fast 200 ack, Redis idempotency on `event_id`, async processing), `ws_broadcaster.py` (client fanout).

## Operating rules (from MASTER.md — non-negotiable)

- **Kill-criterion gate at Phase 1 end:** prove capture → index → search returns a timestamped clip end-to-end BEFORE any UI. If it fails, STOP and ask the user about pivoting to an upload-based "Demo Truth Auditor" — do not push through.
- **Pre-recorded fallback is mandatory.** Every live feature needs a `REPLAY_MODE=true` path serving pre-indexed runs (`task_name = "demo_login_flow"`). Test the replay flow ≥3x before recording the demo.
- **No scope creep.** Anything not in the MASTER.md build plan requires asking first.
- **Production patterns by default:** idempotency keys, retries with exponential backoff (max 3), graceful degradation, env-based config, no secrets in code.
- Every architectural choice gets a one-line "why this over X" comment.

## VideoDB primitives — use and track all 6 in the README

CaptureSession multi-channel (display + mic); scene-level metadata indexing (`task_id`, `run_status`, `divergence_point`); historical RTStream playback; compile search results into playable stream; dual webhook+WebSocket delivery (explain WHY in README); reusable event templates ("unexpected modal," "stuck spinner," "auth failure").

## Observability

Structured JSON logging via `structlog` to stdout. Every request logs: `capture_session_id`, `rtstream_id`, `task_name`, `run_id`, `query_text`, `returned_shot_count`, `relevance_scores`, `compile_job_duration_ms`, `webhook_dedupe_hit`, `claude_token_count`, `e2e_latency_ms`.

## Cost discipline

Screen capture frame density target: **1 frame / 5 seconds** (UI doesn't change every ms; denser sampling burns credits without depth gain — document this in README). Expected ~$2–5 per 10-min capture; sandbox credits give 200+ sessions of headroom — burn liberally on testing.

## When to ask the user

Ask before: adding any dependency outside the stack, changing the killshot UX, skipping the Phase 1 kill-criterion gate, or spending >30 min stuck on one bug. Do NOT ask before: refactoring within a module, adding logging/error handling, writing tests, reading docs.

## Commands

None yet — nothing is scaffolded. Once the Turborepo exists, document the actual build/lint/test/dev commands here (expect Turborepo task runners for `apps/web`, and uvicorn + pytest for `apps/api`; eval suite lives in `apps/api/evals/`).
