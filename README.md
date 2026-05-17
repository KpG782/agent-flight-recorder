# Agent Flight Recorder

**Ask one question — *"Where did the failed run first diverge from the
successful one?"* — and watch two synced video panes scrub to the exact
divergence frame, a red marker lock on the timeline, and a Claude-streamed
plain-English explanation cite the timestamps.**

A forensic black-box recorder for agent/app runs. Not "record your screen and
ask about it" — a **two-run differential**: it replays a success run and a
failure run side by side and pinpoints the first moment they semantically
diverge.

> VideoDB "Eyes and Ears" Global Online Hackathon. Solo build.

---

## 1. Problem

When an agent or app run fails, the question is never "what happened" — it's
**"what happened *differently* this time?"** Logs tell you the error; they don't
show you the first frame where the failed run stopped behaving like the
successful one. Agent Flight Recorder captures runs as video memory and answers
exactly that one question, with the video evidence scrubbed to the moment and an
explanation grounded only in observed events.

The killshot demo: type the canonical question → both panes scrub to the
divergence in lockstep → red timeline marker flares → Claude explains, citing
`T+15.00s`.

## 2. Architecture

```
┌──────────────────────── Desktop Capture Client ─────────────────────────┐
│            (VideoDB-issued token, display + mic channels)               │
└────────────────────────────────┬────────────────────────────────────────┘
                                  ▼  short-lived client token
┌──────────────────────────── FastAPI (apps/api) ─────────────────────────┐
│  capture_orchestrator · indexing · memory_router · evidence_compiler     │
│  search_service · explain_service · webhook_handler · ws_broadcaster     │
│        │                 │                    │                          │
│        ▼                 ▼                    ▼                          │
│   VideoDB SDK        Supabase (Postgres)   Upstash Redis (TLS)           │
│  (media + scenes)    (runs/events/evals)   (idempotency · demo cache)    │
└───────────────┬───────────────────────────────────┬──────────────────────┘
   WebSocket (live, best-effort)        SSE (explanation) + REST (queries)
                ▼                                     ▼
┌──────────── Next.js 15 (apps/web) — split-pane forensic UI ─────────────┐
└──────────────────────────────────────────────────────────────────────────┘
                                  ▲
                  webhooks (durable, at-least-once)
             VideoDB Cloud ── ngrok ──► POST /webhooks/videodb
```

**Dual delivery — why both:** WebSocket alone loses events on disconnect
(unacceptable for forensic truth); webhooks alone add latency that kills the
live UX. Webhooks are the **system of record** (at-least-once, Redis +
`unique(run_id,event_id)` dedupe, async processing after a <50ms ack);
WebSocket is **disposable live view** (at-most-once). Reconciliation always
favors the webhook-persisted record.

**Store boundaries (hard rule):** VideoDB is the sole source of truth for media
+ scene index; Supabase holds run metadata / events / eval results only; Redis
is ephemeral (idempotency keys + the `(task,query)` explanation cache, 1h TTL).

**REPLAY_MODE — the demo cannot fail:** `REPLAY_MODE=true` serves a fully
pre-indexed run pair from a local JSON fixture (`apps/api/fixtures/`), so the
entire killshot flow runs with **no VideoDB, no Supabase, no network**. The
Supabase seed (`migrations/0002_seed_demo.sql`) mirrors the same data for the
live path and the eval suite.

## 3. VideoDB primitives used (all six)

1. **CaptureSession, multi-channel (display + mic)** — `capture_orchestrator.py`
   creates the session and mints a short-lived client token; never ships the API key.
2. **CaptureSession run-scoped metadata + Supabase scene correlation** — run
   metadata rides on `CaptureSession(metadata=...)`; scene→run correlation lives
   in Supabase keyed by `capture_session_id` (per-scene custom tags are an SDK
   gap — documented in `docs/videodb-cheatsheet.md`).
3. **Historical RTStream playback** — `RTStream.generate_stream(start,end)` for
   postmortem rewind without re-capture; `rtstream_id` persisted on `runs`.
4. **Evidence clip from search results** — `evidence_compiler.py` bounds a
   ±`window_s` window around the divergence Unix timestamp and calls
   `generate_stream` (there is no `compile()` on `RTStreamSearchResult`).
5. **Dual webhook + WebSocket delivery** — `webhook_handler.py` (durable) +
   `ws_broadcaster.py` (live); rationale above.
6. **Reusable event templates** — `indexing.ensure_event_templates()` creates
   `unexpected_modal`, `stuck_spinner`, `auth_failure` once and re-attaches them
   as alerts on every run's scene index.

## 4. Eval methodology + numbers

10 labeled cases on `demo_login_flow` (success vs. mistyped-password failure),
run via `python -m src.incident_evaluator` (full table in
`apps/api/evals/results.md`):

| Metric | Value |
|---|---|
| Retrieval precision@3 (mean) | **0.367** (ceiling ≈0.33 — most cases have one relevant shot) |
| Retrieval recall@3 (mean) | **0.783** |
| Top-1 retrieval accuracy | **0.900** |
| Time-to-first-evidence (`/compare`) | **0.4 ms** (replay) |
| Divergence error vs. human label | **0.00 s** |
| Divergence accurate (≤5 s) | **yes** |

Methodology: each case runs `/search` over the failure run for a natural-
language query and scores the top-3 against human-labeled relevant shots.
Divergence accuracy compares the computed first-semantic-divergence to the human
label (15.00s). With sparse (often single-shot) ground truth, p@3's ceiling is
`|relevant|/3` — recall@3 and top-1 accuracy are the faithful signals; both are
reported honestly rather than gamed.

**Embedding choice / trade-off:** divergence + search use a stdlib lexical-
semantic scorer (`similarity.py`: query-coverage + sequence ratio + light
stemming), not a vector model. VideoDB native search is unavailable in replay
(no live stream) and Claude has no embeddings API (Claude is the explanation
layer only); a vector provider would be a dependency outside the fixed stack.
For the short, distinct UI scene descriptions this separates "typed correct
password" from "mistypes the password" deterministically. The `events.embedding`
pgvector column is reserved for the live path.

## 5. Cost model

Screen capture at **1 frame / 5 s** (`CAPTURE_FRAME_INTERVAL_S=5`). UI state
does not change every millisecond — login forms, dashboards, and error banners
persist for seconds — so denser sampling burns VideoDB credits without adding
forensic depth. Expected **~$2–5 per 10-minute capture**; sandbox credits give
**200+ sessions of headroom**, so testing is unconstrained. The demo path
(`REPLAY_MODE`) spends **$0** — it never touches VideoDB.

## 6. Failure modes + mitigations

| Failure mode | Mitigation |
|---|---|
| Live capture unavailable / macOS permission prompt mid-demo | `REPLAY_MODE=true` — zero external deps; demo never touches capture. Verified end-to-end. |
| VideoDB rate limits / transient 5xx | `videodb_client.with_retry` — max 3 attempts, exponential backoff, transient-only. |
| Claude timeout or instability | 8s hard timeout → deterministic template explanation; UI never hard-fails. |
| Webhook duplicates (at-least-once) | Redis `SET NX EX` on `event_id` + `unique(run_id,event_id)` DB backstop. |
| Supabase/DB unreachable | Fixture fallback (`ALLOW_FIXTURE_FALLBACK`) keeps every read path runnable. |
| Clip 404 / slow load | Pane renders a `clip unavailable` frame; the rest of the flow still runs. |
| Divergence false-positive on noise | Tunable `MEMORY_DIVERGENCE_THRESHOLD`; first sub-threshold aligned pair only. |
| Network drop during demo | REPLAY_MODE is fully local; no network on the demo path. |

## 7. Run locally

**Prerequisites:** Python 3.11+, Node 18+, pnpm. Copy `.env.example` → `.env`
and fill keys (VideoDB, Anthropic, Supabase, Upstash Redis `rediss://`).

```bash
# ── API (apps/api) ──
cd apps/api
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# Demo path — zero external deps:
REPLAY_MODE=true uvicorn src.main:app --port 8000
# Eval suite:
REPLAY_MODE=true python -m src.incident_evaluator

# ── Web (apps/web) ──  (separate terminal)
cd apps/web && pnpm install && pnpm dev    # http://localhost:3000

# ── Live path (optional) ──
# 1. Fix DATABASE_URL (Supabase pooler), then: python migrations/apply.py
# 2. ngrok http 8000 ; set WEBHOOK_BASE_URL=https://<sub>.ngrok-free.app
# 3. Run without REPLAY_MODE; point the VideoDB capture client at /sessions/start
```

Open `http://localhost:3000` → it routes straight to the killshot
(`/runs/demo_login_flow/compare`). Press Enter on the prefilled question.

See **`PUNCHLIST.md`** for the items that need a human (DB credentials, real
demo-video capture, ngrok, demo recording + submission).
