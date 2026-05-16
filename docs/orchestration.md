# Multi-Agent Parallel Orchestration Spec

How future Claude Code sessions dispatch sub-agents (Task tool) to build Agent Flight
Recorder with maximum safe parallelism. **A wave starts only when the previous wave's
gate has passed with evidence.** Within a wave, agents run concurrently (single message,
multiple Task calls). Max **3 agents per wave**.

## Agent roster (stable IDs)

| ID | Subagent type | Responsibility | Primary output |
|---|---|---|---|
| `RECON-A` | Explore / general-purpose | Crawl docs.videodb.io | `docs/videodb-cheatsheet.md` |
| `RECON-B` | Explore | Crawl videodb.io/showcase + notebooks | `docs/saturated-patterns.md` |
| `RECON-C` | general-purpose (+ `ui-ux-pro-max`) | UI design recon | UI brief → `specs/phase-3-ui.md` |
| `BE-SCAFFOLD` | general-purpose | Turborepo + FastAPI + Supabase DDL + Redis(TLS) + VideoDB SDK | runnable skeleton |
| `CAPTURE` | general-purpose | `capture_orchestrator.py` + `/sessions/*` | capture endpoints |
| `INDEX` | general-purpose | `index_visuals`/`index_audio` wiring | indexing pipeline |
| `MEMORY` | general-purpose | `memory_router.py` divergence detection | divergence algorithm |
| `EVIDENCE` | general-purpose | `evidence_compiler.py` compile-search-results | playable clip URLs |
| `UI` | general-purpose (+ `ui-ux-pro-max`/`vercel:shadcn`) | Next.js split-pane killshot page | `/runs/[task]/compare` |
| `API-INTEGRATION` | general-purpose | TanStack Query hooks + WS client + SSE consumer | data layer |
| `CLAUDE` | general-purpose (+ `claude-api`) | Sonnet explanation layer + Redis cache | explanation endpoint |
| `RELIABILITY` | general-purpose | webhook idempotency + REPLAY_MODE + demo recording | durable path + replay |
| `EVAL` | general-purpose | eval suite + README metrics | `apps/api/evals/` + table |

## Wave schedule

```
Wave 0   │ RECON-A │ RECON-B │ RECON-C │            (parallel, read-only)
         ▼ GATE: synthesize 3 outputs → update docs/PLAN.md + phase specs

Wave 1   │ BE-SCAFFOLD │ CAPTURE │ INDEX │
           CAPTURE & INDEX consume BE-SCAFFOLD's module layout; if scaffold
           not yet committed, they stub against api-contracts.md then rebase.
         ▼ GATE: KILL-CRITERION — 30s capture → indexed events → NL search
           returns a timestamped clip, end-to-end, proven with logged evidence.
           PASS → Wave 2.  FAIL → STOP, contact user, propose upload-based pivot.

Wave 2   │ MEMORY │ EVIDENCE │                      (parallel)
           Both consume per-run event streams. MEMORY emits divergence_ts;
           EVIDENCE compiles ±10s windows into two playable URLs.
         ▼ GATE: POST /tasks/{name}/compare returns
           { divergence_timestamp, failed_clip_url, success_clip_url }.

Wave 3   │ UI │ API-INTEGRATION │                   (parallel)
           Shared contract: docs/api-contracts.md (frozen before this wave).
         ▼ GATE: split-pane page scrubs both <video> elements to the
           divergence timestamp in sync; red timeline marker renders.

Wave 4   │ CLAUDE │ RELIABILITY │                   (parallel, independent surfaces)
           CLAUDE: SSE-streamed explanation, cited to timestamps, Redis-cached.
           RELIABILITY: webhook idempotency on event_id + REPLAY_MODE + record
           two scripted demo runs (success / mistyped-password failure).
         ▼ GATE: REPLAY_MODE=true demo runs green 3× consecutively.

Wave 5   │ EVAL │ (demo recording + README authoring) │
         ▼ GATE: repo pushed public, submission form filled, eval table in README.
```

## Dependency DAG (must be acyclic)

```
RECON-A ─┐
RECON-B ─┼─► PLAN/specs ─► BE-SCAFFOLD ─┬─► CAPTURE ─┐
RECON-C ─┘                              └─► INDEX ───┴─► [KILL GATE]
                                                            │
                              ┌─────────────────────────────┘
                              ▼
                        MEMORY ─┐
                        EVIDENCE┴─► /compare ─► UI ─┐
                                                    ├─► [SYNC GATE] ─► CLAUDE ─┐
                                          API-INTEGRATION ─┘                   ├─► [REPLAY GATE] ─► EVAL ─► submit
                                                                   RELIABILITY ┘
```
Every agent's inputs are produced by an earlier wave or are external (credentials,
VideoDB cloud) — no cycle.

## Orchestration rules

1. **Never serialize independent work.** Issue all Task calls for a wave in one message.
2. **Max 3 agents per wave.** Pick the 3 highest-leverage independent tracks.
3. **Every agent brief includes:** the architecture diagram (`docs/architecture.md`),
   its relevant `specs/phase-*.md`, the frozen `docs/api-contracts.md`, and the
   stack constraint ("no new deps without asking").
4. **A gate is a hard checkpoint.** The orchestrator must see concrete evidence
   (logged end-to-end run, returned JSON, screenshot/DOM) before dispatching the next wave.
5. **Phase-1 gate failure ⇒ stop and contact the user.** Do not push through; propose
   the Demo Truth Auditor pivot per `specs/phase-1-kill-gate.md`.
6. **Spawning is the expensive path.** Don't dispatch an agent for work the orchestrator
   can do inline faster (small edits, single-file changes).
7. **Replay-first.** RELIABILITY's pre-indexed runs are the demo's safety net; treat
   recording + 3× replay verification as release-blocking, not optional polish.
