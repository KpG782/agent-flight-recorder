# Claude Code Mega-Prompt: Agent Flight Recorder Build

Copy-paste this entire block into Claude Code in a fresh directory. It's structured to maximize sub-agent parallelism, MCP usage, and skill invocation.

---

```
# AGENT FLIGHT RECORDER — VideoDB Hackathon Build

You are my Staff/Principal AI Engineer pair. We are building **Agent Flight Recorder** for the VideoDB "Eyes and Ears" Global Online Hackathon. Submission deadline: May 18, 2026, 12:30 PM Manila time. Hard solo build window: ~28 hours remaining.

## NON-NEGOTIABLE OPERATING RULES

1. **Think in trade-offs, always.** Every architectural choice gets a one-line "why this over X" comment.
2. **Layman analogy first, then principal-level depth.** I want to understand, not copy-paste.
3. **Production patterns by default:** idempotency keys, retries with backoff, graceful degradation, structured logging, env-based config, no secrets in code.
4. **Ship the kill-criterion gate first.** Do not write UI until the capture → index → search loop is proven end-to-end.
5. **Pre-recorded fallback is mandatory.** Every live feature must have a "replay mode" toggle so the demo cannot fail.
6. **No scope creep.** If something isn't on the build plan below, ask before adding it.

## STACK (fixed)

- **Backend:** FastAPI (Python 3.11+), uvicorn
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui
- **DB:** Supabase (Postgres) — run metadata, labels, eval results only
- **Cache/Queue:** Redis — idempotency keys, hot event fanout, demo cache
- **Media memory:** VideoDB (source of truth — do NOT duplicate media into Supabase)
- **LLM:** Claude API (Sonnet) — only for final natural-language divergence explanation, NOT for retrieval orchestration
- **Monorepo:** Turborepo with `apps/web` (Next.js) and `apps/api` (FastAPI), shared `packages/types`
- **Deploy target:** local for demo, Vercel for web fallback, ngrok tunnel for webhooks during demo

## SUB-AGENT DELEGATION PLAN

Use the Task tool aggressively. Spawn sub-agents in parallel wherever the work is independent. Do NOT serialize work that could run concurrently.

**Phase 0 — Recon (run these 3 sub-agents IN PARALLEL):**

- **Sub-agent A — VideoDB Doc Crawler:** Use `context7` MCP if available, else `web_fetch` on https://docs.videodb.io. Produce a single `docs/videodb-cheatsheet.md` covering: CaptureSession lifecycle, RTStream retrieval, index_visuals params + prompt tuning, index_audio, search (keyword + semantic), compile search results into stream, webhook payload schema, WebSocket event schema, alert/event template system, scene-level metadata, historical RTStream playback with start/end. Include exact Python SDK call signatures.
- **Sub-agent B — Showcase Differentiator:** Crawl https://videodb.io/showcase and https://notebooks.videodb.io. Produce `docs/saturated-patterns.md` listing what's already been built so we explicitly avoid those framings in our README and demo narrative.
- **Sub-agent C — Frontend Design Recon:** Read `/mnt/skills/public/frontend-design/SKILL.md` end-to-end. Then produce `docs/ui-design-brief.md` proposing the split-pane forensic UI: failed-run pane | successful-run pane | prompt bar | divergence timeline. Reference shadcn/ui components. Use Obra-style "calm forensic tool" aesthetic — think Linear meets a flight black-box recorder. Dark mode primary.

Wait for all three to complete. Synthesize findings into `PLAN.md` before writing any code.

## REQUIRED SKILLS TO INVOKE

Before writing or modifying files, `view` the relevant SKILL.md from `/mnt/skills/public/`:

- `frontend-design/SKILL.md` — mandatory before any UI work
- `product-self-knowledge/SKILL.md` — before any Claude API calls
- `docx/SKILL.md` — only if I ask for a written report later

Treat these as authoritative.

## ARCHITECTURE (final, no debate)

```
┌──────────────────────────────────────────────────────────┐
│                  Desktop Capture Client                  │
│        (VideoDB-issued, display + mic channels)          │
└────────────────────────────┬─────────────────────────────┘
                             │ short-lived token
                             ▼
┌──────────────────────────────────────────────────────────┐
│                   FastAPI (apps/api)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ CaptureOrch  │  │ MemoryRouter │  │ EvidenceComp │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │            │
│         ▼                 ▼                 ▼            │
│  ┌──────────────────────────────────────────────────┐    │
│  │              VideoDB SDK (Python)                │    │
│  └──────────────────────────────────────────────────┘    │
│         │                 │                              │
│         ▼                 ▼                              │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │  Supabase    │  │    Redis     │                      │
│  │  (metadata)  │  │ (idempotency)│                      │
│  └──────────────┘  └──────────────┘                      │
└────────────────────────────┬─────────────────────────────┘
                             │ WebSocket (live) + REST (queries)
                             ▼
┌──────────────────────────────────────────────────────────┐
│            Next.js 15 (apps/web) — Split-Pane UI         │
└──────────────────────────────────────────────────────────┘
                             ▲
                             │ webhooks (durable, at-least-once)
                             │
                        VideoDB Cloud
```

**Core modules in `apps/api/src/`:**

- `capture_orchestrator.py` — creates CaptureSession, mints token, wires channels
- `memory_router.py` — fetches indexed events per run, embeds, finds divergence
- `evidence_compiler.py` — calls VideoDB compile-search-results, returns playable URLs
- `incident_evaluator.py` — runs the eval suite on labeled test pairs
- `webhook_handler.py` — fast 200 ack, Redis idempotency, async processing
- `ws_broadcaster.py` — fanout to connected clients

## BUILD PLAN — execute in this order

### Phase 1: Kill-Criterion Gate (4 hours, HARD STOP)

Spawn sub-agents in parallel:
- **Backend agent:** scaffold Turborepo + FastAPI + Supabase schema (tables: `runs`, `events`, `eval_cases`) + Redis client + VideoDB SDK wiring
- **Capture agent:** write `capture_orchestrator.py` with one endpoint `POST /sessions/start` that returns a client token, and `POST /sessions/{id}/end`
- **Indexing agent:** wire `index_visuals` with this prompt — *"Identify visible UI elements, button clicks, page transitions, error states, modal dialogs, form submissions, and authentication screens. Be specific about what app or page is shown and any text visible."* — and `index_audio` for mic transcription

**Gate check at hour 4:** can I capture a 30-second session, get indexed events back, and run one natural-language search that returns a timestamped clip? If NO → **stop and tell me to pivot to Demo Truth Auditor (upload-based)**. Do not push through.

### Phase 2: Two-Run Comparison Core (hours 4–10)

- Implement run tagging: `task_name`, `run_status` (success/failure), `app_version`, `started_at`, `ended_at`
- `memory_router.py`: given `task_name`, fetch both runs' event streams, embed event descriptions (use Claude API's embeddings or VideoDB's native search), compute first semantic divergence point
- `evidence_compiler.py`: take divergence timestamp + window (±10 sec), return compiled playable stream URLs for both runs
- Endpoint: `POST /tasks/{name}/compare` → returns `{ divergence_timestamp, failed_clip_url, success_clip_url, explanation }`

### Phase 3: Killshot UI (hours 10–16)

Invoke `frontend-design` skill first. Then spawn:
- **UI agent:** Next.js 15 split-pane page at `/runs/[task]/compare`. Two `<video>` elements synced via shared timeline state. shadcn/ui for prompt bar, command palette (`Cmd+K`), event rail. Tailwind dark theme. Forensic aesthetic — monospace timestamps, subtle red glow on divergence marker, no rounded-corner SaaS friendliness.
- **API integration agent:** TanStack Query hooks for `/compare`, WebSocket connection for live events, optimistic state updates

The killshot moment: user types *"Where did the failed run first diverge from the successful one?"* → both videos scrub to divergence timestamp in sync → red marker appears on timeline → Claude's plain-English explanation streams in below.

### Phase 4: Divergence Logic + Claude Integration (hours 16–22)

- Wire Claude API (Sonnet) with tool use for the explanation layer ONLY
- System prompt: *"You are a forensic agent analyst. Given two event sequences (one successful, one failed) and the identified divergence point, explain in 2-3 sentences what went wrong and why. Cite specific timestamped evidence. Do not speculate beyond the provided events."*
- Cache `(task_name, query)` → response in Redis with 1-hour TTL so demo replays are instant
- Stream the response to the UI via SSE

### Phase 5: Reliability + Fallback (hours 22–28)

- Webhook handler: ack 200 in <50ms, push to Redis queue, process async with idempotency on `event_id`
- WebSocket: at-most-once is fine for live UX (state of truth lives in webhook path)
- **MANDATORY:** record two real capture sessions of a scripted task (e.g., "log into a demo SaaS dashboard" — success run vs. failure run where the password field is mistyped). Pre-index both. Store as `task_name = "demo_login_flow"`. Add a `REPLAY_MODE=true` env flag that bypasses live capture entirely and serves these as the demo. **Test the replay flow at least 3 times before recording the demo video.**

### Phase 6: Demo + Submission (hours 28–33)

- Record 90-second demo video. Opening 15 seconds must show the killshot.
- README sections: Problem, Architecture diagram, VideoDB primitives used (list all 6), Eval methodology + numbers, Cost model, Failure modes + mitigations, How to run locally
- Eval suite: 10 labeled test pairs in `apps/api/evals/`. Measure: retrieval precision@3, time-to-first-evidence (ms), divergence accuracy (within 5 sec of human label). Put the table in the README.
- Push public GitHub repo
- Fill submission form

## VIDEODB PRIMITIVES TO EXPLICITLY USE (depth score = 30%)

Track these in the README. Every shallow submission uses 2. We use 6:

1. CaptureSession with multi-channel (display + mic)
2. Scene-level metadata indexing (`task_id`, `run_status`, `divergence_point`)
3. Historical RTStream playback (start/end timestamps for postmortem rewind)
4. Compile search results into playable stream (the evidence clip)
5. Dual delivery — webhooks for durability + WebSocket for live UX (explain WHY in README — that's the principal signal)
6. Reusable event templates — "unexpected modal," "stuck spinner," "auth failure" — attached across runs

## OBSERVABILITY (non-negotiable)

Every request logs: `capture_session_id`, `rtstream_id`, `task_name`, `run_id`, `query_text`, `returned_shot_count`, `relevance_scores`, `compile_job_duration_ms`, `webhook_dedupe_hit` (bool), `claude_token_count`, `e2e_latency_ms`. Use `structlog` in Python. Pipe to stdout JSON for the demo; production would route to Datadog/Logfire.

## COST MODEL (for the README)

VideoDB pricing model:
- Realtime ingest: per signal-hour
- Transcription: per minute
- Scene processing: per scene
- Search: per 1,000 queries
- ~1 frame ≈ 1K model tokens

Frame density target: **1 frame / 5 seconds** for screen capture. UI doesn't change every millisecond — denser sampling burns credits without depth gain. Document this trade-off in the README as a principal-level decision.

Expected demo session cost: **$2–5 per 10-minute capture**. With $1,000 sandbox credits, that's 200+ full sessions of headroom. Burn liberally on testing; that's what the credits are for.

## FAILURE MODES TO PRE-EMPT

| Risk | Mitigation |
|---|---|
| Capture permission prompt mid-demo | Grant all perms before recording, restart machine, test 3x |
| Indexing lag (2–5 sec live) | Capture happens off-camera in demo; ask questions on pre-indexed data |
| Webhook duplicates | Redis idempotency keys on `event_id` |
| Vision model misreads dense UI | Use clean demo app (large buttons, clear text — NOT a Grafana panel) |
| Network drops during live demo | REPLAY_MODE flag with pre-indexed runs |
| VideoDB rate limits | Exponential backoff in SDK wrapper, max 3 retries |
| Claude API timeout | 8-second hard timeout, fallback to template explanation |

## WHEN TO ASK ME

Ask before:
- Adding any dependency not in the stack list above
- Changing the killshot UX
- Skipping the kill-criterion gate at hour 4
- Spending more than 30 min stuck on any single bug

Do NOT ask before:
- Refactoring within a module
- Adding logging or error handling
- Writing tests
- Reading docs via context7 or web_fetch

## START SEQUENCE

1. Confirm my OS and check VideoDB desktop capture client compatibility (macOS / Windows only — I'm on macOS M4 Air, confirm this is supported before anything else)
2. View the three required skill files
3. Spawn Phase 0 recon sub-agents in parallel (A, B, C)
4. Wait for all three, synthesize into `PLAN.md`
5. Show me `PLAN.md` and wait for my "go" before Phase 1

Go.
```

---

## How to use this — layman's explanation

Think of this prompt like a **mission briefing for a SEAL team**. Claude Code is the commander, and the sub-agents are the operators. The briefing tells the commander:

1. **What the mission is** (build Agent Flight Recorder)
2. **Hard rules of engagement** (kill-criterion gate, no scope creep, fallback mandatory)
3. **Team structure** (which sub-agents handle what, run in parallel where possible)
4. **Equipment list** (the fixed stack — no debate)
5. **Phased execution** (Phase 0 → 6, with gates)
6. **When to radio back to HQ (you)** vs. just execute

## Why this prompt is structured this way

| Section | Why it's there |
|---|---|
| **Non-negotiable rules** | Stops Claude Code from drifting into scope creep or pretty-but-useless refactors |
| **Phase 0 parallel sub-agents** | Three independent recon jobs → 3x speedup vs. sequential. This is the "multi-agent" leverage you asked about. |
| **Skill invocation list** | Forces Claude Code to read `frontend-design/SKILL.md` *before* writing UI — that's the "Obra UX pro max" hook. The skill itself contains the design rules. |
| **Architecture diagram** | Anchors every sub-agent to the same mental model. No diverging implementations. |
| **Killshot UX spec** | One paragraph that locks in the demo moment. Everything else serves it. |
| **VideoDB primitives checklist** | Direct mapping to the 30% depth score. Every primitive used = points banked. |
| **Cost model + failure modes** | Principal-level README content pre-written. Saves you 1 hour at the end. |
| **Start sequence** | Explicit first 5 actions. No ambiguity. Claude Code starts moving immediately. |

## What you do RIGHT NOW

1. Open Claude Code in a fresh empty directory: `mkdir agent-flight-recorder && cd agent-flight-recorder && claude`
2. Paste the entire prompt above (everything between the triple backticks)
3. Claude Code will confirm your OS and start Phase 0
4. **Stay at the keyboard for hour 4** — the kill-criterion gate decision needs your "go" or "pivot" call
5. After that, you mostly supervise. Spot-check every 2 hours. Don't micromanage the sub-agents.

## One honest note before you fire

The prompt assumes Claude Code can run sub-agents via the Task tool, has `context7` MCP available (you have n8n MCP configured but I don't see context7 in your connected list — if it's not there, Claude Code will fall back to `web_fetch`, which is fine, just slower). If you want context7 specifically, install it as an MCP server before you start — but don't let that delay you past 30 minutes. The build matters more than the tooling.

Go ship it. Check in at hour 4 with the kill-criterion result.