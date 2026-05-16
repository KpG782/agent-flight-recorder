# Data Model — Supabase (Postgres)

Supabase stores **metadata, labels, and eval results only**. Media + scene index live
in VideoDB and are referenced by ID. No media bytes in Postgres.

## Tables

### `runs`
One row per captured run of a task.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK default `gen_random_uuid()` | |
| `task_name` | `text` not null | logical grouping; success/failure runs share this |
| `run_status` | `text` not null | `success` \| `failure` \| `in_progress` |
| `app_version` | `text` | optional tag of the app under test |
| `capture_session_id` | `text` | VideoDB CaptureSession id |
| `rtstream_id` | `text` | VideoDB RTStream id (for historical playback) |
| `started_at` | `timestamptz` not null | |
| `ended_at` | `timestamptz` | null while in progress |
| `created_at` | `timestamptz` default `now()` | |

Index: `(task_name, run_status)`, `(task_name, started_at desc)`.

### `events`
Indexed scene-level events delivered via webhook (deduped before insert).

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK default `gen_random_uuid()` | |
| `run_id` | `uuid` FK → `runs.id` on delete cascade | |
| `event_id` | `text` not null | VideoDB event id — **unique idempotency key** |
| `t_offset_s` | `numeric` not null | seconds from run start |
| `channel` | `text` | `display` \| `mic` |
| `description` | `text` | scene/transcript text used for embedding |
| `template_tag` | `text` | reusable template: `unexpected_modal` \| `stuck_spinner` \| `auth_failure` \| null |
| `embedding` | `vector` | pgvector; nullable until embedded |
| `raw` | `jsonb` | full webhook payload for audit |
| `created_at` | `timestamptz` default `now()` | |

Constraint: `unique (run_id, event_id)` — enforces idempotency at the DB layer in
addition to the Redis dedupe.
Index: `(run_id, t_offset_s)`; ivfflat on `embedding` if pgvector enabled.

### `eval_cases`
Labeled test pairs for the eval suite (10 pairs target).

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK default `gen_random_uuid()` | |
| `task_name` | `text` not null | |
| `success_run_id` | `uuid` FK → `runs.id` | |
| `failure_run_id` | `uuid` FK → `runs.id` | |
| `human_divergence_s` | `numeric` not null | ground-truth divergence offset |
| `query_text` | `text` | canonical NL query for precision@3 |
| `expected_shot_ids` | `text[]` | ground-truth relevant shots |
| `notes` | `text` | |
| `created_at` | `timestamptz` default `now()` | |

## Rationale

- `event_id` unique-per-run mirrors the Redis idempotency key so a Redis flush can't
  cause duplicate inserts — DB is the backstop, Redis is the fast path.
- `embedding` is nullable so webhook ingest stays fast (<50ms ack); embedding is a
  separate async step in `memory_router`.
- `template_tag` enables VideoDB primitive #6 (reusable event templates) to be queried
  across runs (`select … where template_tag = 'auth_failure'`).
- `rtstream_id` on `runs` enables primitive #3 (historical RTStream playback) for
  postmortem rewind without re-capture.

## Migration ordering

`runs` → `events` (FK) → `eval_cases` (FK to runs). Enable `pgcrypto`
(`gen_random_uuid`) and `vector` (pgvector) extensions first.
