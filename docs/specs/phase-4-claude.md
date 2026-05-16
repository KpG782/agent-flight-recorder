# Phase 4 — Claude Divergence Explanation

**Objective:** Plain-English, evidence-cited explanation of what went wrong, streamed to
the UI. Claude is used **here only** — never for retrieval orchestration.

**Inputs / preconditions:** Phase-3 gate PASSED; `/compare` returns divergence +
clips + `divergence_event_ids`; `claude-api` skill invoked (prompt caching enabled).

**Parallel agent assignments (Wave 4 — 2 concurrent, independent surfaces):**
- `CLAUDE`: implement `GET /tasks/{task_name}/explain?query=...` SSE per
  `api-contracts.md`. Build the success/failure event sequences + divergence point;
  call Claude (`CLAUDE_MODEL`) with the system prompt below; stream tokens as SSE
  `token` events. Cache `(task_name, query)` → full response in Redis,
  `REDIS_DEMO_CACHE_TTL_S` (1h) — cache hit replays instantly. **8s hard timeout
  (`CLAUDE_TIMEOUT_S`) → fall back to a template explanation; never hard-fail the UI.**
- `RELIABILITY`: runs concurrently — see `phase-5-reliability.md` (separate surface).

System prompt (verbatim from MASTER):
> "You are a forensic agent analyst. Given two event sequences (one successful, one
> failed) and the identified divergence point, explain in 2-3 sentences what went wrong
> and why. Cite specific timestamped evidence. Do not speculate beyond the provided
> events."

**Concrete tasks:** assemble the two event sequences from `events`; pass divergence
context; enable prompt caching on the static system/instruction prefix; log
`claude_token_count` and `e2e_latency_ms`.

**Acceptance criteria:** for `demo_login_flow` the streamed explanation is 2–3 sentences,
cites at least one timestamp, and does not invent events; a repeat query returns from
Redis cache (`done.cached=true`) noticeably faster.

**Gate / exit:** explanation streams and is cited to timestamps → dispatch Wave 5.

**Risks:** Claude timeout/instability (template fallback path tested explicitly);
hallucinated events (constrain prompt to provided events only; spot-check); cache key
collisions (normalize query text before hashing).
