# Architecture

## Component diagram

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
│         ▼                 ▼                 ▼            │
│  ┌──────────────────────────────────────────────────┐    │
│  │              VideoDB SDK (Python)                │    │
│  └──────────────────────────────────────────────────┘    │
│         │                 │                              │
│         ▼                 ▼                              │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │  Supabase    │  │ Upstash Redis│                      │
│  │ (metadata)   │  │(idempotency) │                      │
│  └──────────────┘  └──────────────┘                      │
└────────────────────────────┬─────────────────────────────┘
              WebSocket (live) │ + REST (queries) + SSE (explanation)
                             ▼
┌──────────────────────────────────────────────────────────┐
│            Next.js 15 (apps/web) — Split-Pane UI         │
└──────────────────────────────────────────────────────────┘
                             ▲
                             │ webhooks (durable, at-least-once)
                        VideoDB Cloud  ── ngrok ──► /webhooks/videodb
```

## Core `apps/api/src/` modules

| Module | Responsibility |
|---|---|
| `capture_orchestrator.py` | Create CaptureSession, mint short-lived client token, wire display+mic channels |
| `memory_router.py` | Per `task_name`, fetch both runs' event streams, embed descriptions, compute first semantic divergence point |
| `evidence_compiler.py` | Call VideoDB compile-search-results for divergence ±10s window → playable URLs |
| `incident_evaluator.py` | Run eval suite over labeled test pairs in `apps/api/evals/` |
| `webhook_handler.py` | Ack 200 in <50ms, Redis idempotency on `event_id`, async processing |
| `ws_broadcaster.py` | Fan out live events to connected WebSocket clients |

## Data flow

1. Client starts a session → `capture_orchestrator` returns token; display + mic stream to VideoDB.
2. VideoDB indexes scenes (`index_visuals` + `index_audio`) and emits events.
3. **Two delivery paths:**
   - **Webhooks → `webhook_handler`** = the *state of truth*. At-least-once; deduped via
     Redis `event_id` keys; processed async; persisted to Supabase.
   - **WebSocket → `ws_broadcaster`** = best-effort *live UX only*. At-most-once is fine
     because truth lives in the webhook path.
4. Query time: `memory_router` pulls both runs' events, finds divergence; `evidence_compiler`
   compiles two clips; `CLAUDE` layer streams an explanation over SSE.

### Why dual delivery (the principal signal for the README)

WebSocket alone loses events on disconnect — unacceptable for forensic truth.
Webhooks alone add latency that kills the live "watch it happen" UX. Using webhooks as
the durable system of record and WebSocket as a disposable live view gives both
reliability and responsiveness without a queue per client. State reconciliation always
favors the webhook-persisted record.

## Store boundaries (hard rule)

- **VideoDB** = sole source of truth for media + scene index. Never copy media into Supabase.
- **Supabase** = run metadata, labels, eval results only (see `data-model.md`).
- **Redis (Upstash, TLS)** = webhook idempotency keys, hot event fanout buffer, demo
  response cache (`(task_name, query)` → explanation, 1h TTL). Ephemeral; never the source of truth.

## Boundaries / runtime notes

- Upstash URL is `rediss://` — `redis-py` must connect with TLS enabled.
- VideoDB Cloud webhooks need a public URL → `ngrok` tunnel; configured via `WEBHOOK_BASE_URL`.
- Claude is invoked **only** in the explanation layer, never for retrieval orchestration,
  with an 8s hard timeout falling back to a template explanation.
