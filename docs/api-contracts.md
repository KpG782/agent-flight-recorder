# API Contracts — FastAPI (`apps/api`)

Frozen before Wave 3 so `UI` and `API-INTEGRATION` build against a stable shape.
All errors use `{ "error": { "code": str, "message": str } }` with appropriate HTTP status.
All responses logged with the observability field set (see `PLAN.md`).

## Sessions (Phase 1)

### `POST /sessions/start`
Create a CaptureSession and mint a short-lived client token.

Request:
```json
{ "task_name": "demo_login_flow", "run_status": "in_progress", "app_version": "v1" }
```
Response `200`:
```json
{
  "run_id": "uuid",
  "capture_session_id": "vdb_...",
  "client_token": "short-lived-jwt",
  "expires_at": "2026-05-17T12:00:00Z"
}
```

### `POST /sessions/{run_id}/end`
Finalize a run.

Request: `{ "run_status": "success" | "failure" }`
Response `200`: `{ "run_id": "uuid", "rtstream_id": "vdb_...", "ended_at": "..." }`

## Search (Phase 1 — kill-criterion)

### `POST /search`
Natural-language search over a run's indexed events; returns timestamped shots.
Backed by **`RTStream.search` (semantic)** — collection keyword search raises
`NotImplementedError` in the SDK (see `videodb-cheatsheet.md`).

Request: `{ "run_id": "uuid", "query": "where did login fail", "k": 3 }`
Response `200`:
```json
{
  "shots": [
    { "shot_id": "s1", "t_start_s": 42.0, "t_end_s": 47.0,
      "score": 0.81, "description": "...", "clip_url": "https://..." }
  ],
  "returned_shot_count": 3,
  "e2e_latency_ms": 1234
}
```
This endpoint passing end-to-end **is** the Phase-1 kill-criterion gate.

## Compare (Phase 2)

### `POST /tasks/{task_name}/compare`
Find first divergence between the task's success and failure runs and compile evidence clips.

Request (optional overrides):
```json
{ "success_run_id": "uuid", "failure_run_id": "uuid", "window_s": 10 }
```
Response `200`:
```json
{
  "task_name": "demo_login_flow",
  "divergence_timestamp": 42.5,
  "failed_clip_url": "https://videodb.../compiled_fail.m3u8",
  "success_clip_url": "https://videodb.../compiled_success.m3u8",
  "explanation": null,
  "divergence_event_ids": { "success": "e_12", "failure": "e_15" }
}
```
`explanation` is filled by the Phase-4 SSE endpoint, not inline.

## Explanation (Phase 4)

### `GET /tasks/{task_name}/explain?query=...` (SSE)
Server-Sent Events stream of the Claude Sonnet explanation, cited to timestamps.
Cache key `(task_name, query)` in Redis, 1h TTL — cache hit replays instantly.
Events: `token` (partial text), `done` (`{ "cached": bool, "claude_token_count": int }`),
`error` (falls back to a template explanation; never hard-fails the UI).

## Webhooks (Phase 5)

### `POST /webhooks/videodb`
VideoDB Cloud event delivery via `ngrok`. **Ack `200` in <50ms.**
Behavior: validate envelope shape (no HMAC/signature exists in the VideoDB SDK or
docs — trust boundary is the secret `ngrok` URL + `event_id` idempotency) → check
Redis idempotency key on `event_id` (hit ⇒ return `200` immediately,
`webhook_dedupe_hit=true`) → push to async processing → persist to `events` with
`unique(run_id, event_id)` backstop. Normalize event timestamps to seconds on ingest
(VideoDB WS/webhook units are inconsistent ms/s — see `videodb-cheatsheet.md`).
Response `200`: `{ "received": true }` (always fast, even on dedupe).

## WebSocket (Phase 3/5)

### `WS /ws?run_id=...`
Live event fanout for the active run (best-effort, at-most-once).
Server → client frames: `{ "type": "event", "run_id", "t_offset_s", "description", "template_tag" }`.
Truth still lives in the webhook path; WS is disposable live UX.

## Health

### `GET /healthz`
`{ "status": "ok", "replay_mode": bool, "videodb": "ok", "redis": "ok", "supabase": "ok" }`
