# Agent Flight Recorder — Master Plan

> Synthesized from `MASTER.md` (authoritative). This file is the entry point; per-phase
> detail lives in `docs/specs/`, cross-cutting detail in the sibling docs.

## Goal

A forensic "black-box recorder" for agent/app runs. Capture runs as video memory via
VideoDB, then answer one killer question — **"Where did the failed run first diverge
from the successful one?"** — by scrubbing two synced video panes to the divergence
timestamp with a Claude-streamed plain-English explanation.

**Hackathon:** VideoDB "Eyes and Ears" Global Online Hackathon.
**Deadline:** 2026-05-18, 12:30 PM Manila time. Solo build.
**Demo target:** local for the live demo; Vercel for web fallback; `ngrok` for webhooks.

## Fixed stack (no deviation without asking the user)

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python 3.11+), uvicorn — `apps/api` |
| Frontend | Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui — `apps/web` |
| Monorepo | Turborepo, shared `packages/types` |
| Metadata DB | Supabase (Postgres) — run metadata, labels, eval results ONLY |
| Cache/Queue | **Upstash Redis** (hosted, TLS `rediss://`) |
| Media memory | VideoDB — source of truth; never duplicate media into Supabase |
| LLM | Claude API (Sonnet) — final NL divergence explanation ONLY |

## Phase index

| Phase | Spec | Gate |
|---|---|---|
| 0 — Recon | `specs/phase-0-recon.md` | 3 recon docs synthesized into this PLAN |
| 1 — Kill-criterion gate | `specs/phase-1-kill-gate.md` | **HARD STOP**: capture→index→search→clip end-to-end |
| 2 — Two-run comparison | `specs/phase-2-comparison.md` | `/tasks/{name}/compare` returns divergence + 2 clip URLs |
| 3 — Killshot UI | `specs/phase-3-ui.md` | Both videos scrub to divergence in sync |
| 4 — Claude + divergence | `specs/phase-4-claude.md` | Streamed explanation cited to timestamps |
| 5 — Reliability + fallback | `specs/phase-5-reliability.md` | REPLAY_MODE demo green 3× |
| 6 — Demo + submission | `specs/phase-6-demo.md` | Repo pushed, form filled, eval table in README |

Multi-agent dispatch for every phase is governed by `docs/orchestration.md`.

## Wave 0 recon — confirmed corrections (authoritative; supersedes MASTER.md)

Synthesized from `docs/videodb-cheatsheet.md` (RECON-A, quoted from SDK source),
`docs/saturated-patterns.md` (RECON-B), and the UI brief in `specs/phase-3-ui.md` (RECON-C).

1. **Env var name:** the SDK reads **`VIDEO_DB_API_KEY`** (not `VIDEODB_API_KEY`).
   `.env`/`.env.example` use `VIDEO_DB_API_KEY` + `VIDEO_DB_BASE_URL`. pydantic-settings
   must expose these exact names; `videodb.connect()` auto-reads `VIDEO_DB_API_KEY`.
   Install extras: `pip install "videodb[capture,websockets]"`.
2. **Primitive #2 reframed — scene-level *custom* metadata is a GAP.** There is no SDK
   call to attach arbitrary `task_id`/`run_status`/`divergence_point` onto live RTStream
   scene records. **Approach:** set run metadata via `CaptureSession(metadata=...)` at
   session creation and correlate scenes → run in **Supabase** (the `runs`/`events`
   join). Primitive #2 is now "**CaptureSession run-scoped metadata + Supabase scene
   correlation**" — still a legitimate, documentable primitive; just not per-scene tags.
3. **Webhook trust boundary — no HMAC/signature exists.** Durability rests on the
   `ngrok` URL being secret + Redis/`event_id` idempotency. `api-contracts.md` updated:
   "verify signature" → "validate envelope shape + `event_id` dedupe" (no signature).
4. **Search:** Collection keyword search raises `NotImplementedError`; use
   **`RTStream.search` (semantic)**. `/search` and `/compare` build on RTStream search.
5. **WS:** real method is `ws.receive()` (not `ws.stream()`); event timestamp units
   are inconsistent (ms vs s) — normalize to seconds at the ingest boundary.
6. **Positioning (RECON-B):** the ecosystem is saturated with single-stream
   "record screen → ask in natural language" and "give your agent eyes and ears"
   framings. **Avoid those phrases** in README/demo. Our uncontested lane: two-run
   *differential / divergence* forensic replay. Demo opens **on the killshot**, never
   on "watch me capture my screen." Enforced in `specs/phase-6-demo.md`.

## Skill substitution (environment adaptation)

`MASTER.md` instructs viewing `/mnt/skills/public/{frontend-design,product-self-knowledge,docx}/SKILL.md`.
**These do not exist on this local macOS machine.** Substitutes (authoritative for this build):

| MASTER.md reference | Use instead |
|---|---|
| `frontend-design/SKILL.md` | `ui-ux-pro-max` skill + `vercel:shadcn` skill |
| `product-self-knowledge/SKILL.md` | `claude-api` skill (for the Claude integration layer) |
| `docx/SKILL.md` | N/A — only if a written report is requested later |

`brainstorming` / `writing-plans` / `test-driven-development` / `verification-before-completion`
from the superpowers set still apply to their respective activities.

## Kill-criterion gate (the single most important rule)

At the end of Phase 1: **can we capture a 30-second session, get indexed events back,
and run one natural-language search that returns a timestamped clip?**
- **YES** → proceed to Phase 2.
- **NO** → STOP. Do not push through. Contact the user and propose the pivot to
  **Demo Truth Auditor** (upload-based, no live capture). See `specs/phase-1-kill-gate.md`.

## Fallback strategy (mandatory)

Every live feature must work in `REPLAY_MODE=true`, which bypasses live capture and
serves two pre-indexed runs stored under `DEMO_TASK_NAME=demo_login_flow`
(success run vs. failure run with a mistyped password). The replay flow must be
tested **≥3 times** before recording the demo video. Detail in `specs/phase-5-reliability.md`.

## Cost discipline

Screen capture at **1 frame / 5 s** (`CAPTURE_FRAME_INTERVAL_S=5`) — UI doesn't change
every ms; denser sampling burns credits without depth gain. Expected ~$2–5 per 10-min
capture; sandbox credits give 200+ sessions of headroom. Document the trade-off in the README.

## Six VideoDB primitives (README depth score = 30%)

1. CaptureSession with multi-channel (display + mic)
2. CaptureSession run-scoped metadata + Supabase scene correlation (see Wave 0 note #2 — per-scene custom tags are not an SDK primitive)
3. Historical RTStream playback (start/end timestamps for postmortem rewind)
4. Compile search results into a playable stream (the evidence clip)
5. Dual delivery — webhooks for durability + WebSocket for live UX (explain WHY)
6. Reusable event templates ("unexpected modal", "stuck spinner", "auth failure")

## Observability (non-negotiable)

`structlog` JSON to stdout. Every request logs: `capture_session_id`, `rtstream_id`,
`task_name`, `run_id`, `query_text`, `returned_shot_count`, `relevance_scores`,
`compile_job_duration_ms`, `webhook_dedupe_hit`, `claude_token_count`, `e2e_latency_ms`.

## When to ask the user

Ask before: adding a dependency outside the stack; changing the killshot UX; skipping
the Phase-1 gate; spending >30 min stuck on one bug. Do **not** ask before: refactoring
within a module, adding logging/error handling, writing tests, reading docs.
