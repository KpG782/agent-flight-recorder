# Phase 2 — Two-Run Comparison Core

**Objective:** Given a `task_name` with a success run and a failure run, compute the
first semantic divergence point and compile a playable evidence clip for each.

**Inputs / preconditions:** Phase-1 gate PASSED; `/search` works; `runs`/`events`
tables populated; `videodb-cheatsheet.md` covers compile-search-results + search scoring.

**Parallel agent assignments (Wave 2 — 2 concurrent):**
- `MEMORY`: `memory_router.py`. Given `task_name`, fetch both runs' event streams from
  Supabase; embed event descriptions (VideoDB native search or Claude embeddings —
  pick per cheatsheet, document the trade-off); align sequences by `t_offset_s`;
  compute the **first semantic divergence point** (first index where the success and
  failure event semantics meaningfully differ). Emit `divergence_timestamp` +
  `divergence_event_ids`.
- `EVIDENCE`: `evidence_compiler.py`. Given the divergence timestamp ± `window_s`
  (default 10), call VideoDB compile-search-results for each run → two playable URLs.

**Concrete tasks:** implement `POST /tasks/{task_name}/compare` per `api-contracts.md`,
returning `{ divergence_timestamp, failed_clip_url, success_clip_url,
divergence_event_ids, explanation: null }`. Run tagging fields (`task_name`,
`run_status`, `app_version`, `started_at`, `ended_at`) populated on the `runs` rows.

**Acceptance criteria:** for `task_name=demo_login_flow`, `/compare` returns a numeric
`divergence_timestamp` and two distinct, playable clip URLs; divergence is within ~5s
of a manual eyeball of the two runs.

**Gate / exit:** `POST /tasks/{task_name}/compare` returns valid divergence + two
playable URLs → dispatch Wave 3.

**Risks:** embeddings too coarse to separate similar UI states (tune description
granularity from `index_visuals`; consider template_tag-aware comparison); off-by-window
clip bounds (clamp to run start/end); divergence false-positive on noise (compare on
template-tagged or high-salience events first).
