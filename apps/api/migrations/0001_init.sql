-- Agent Flight Recorder — initial schema.
-- Mirrors docs/data-model.md exactly. Supabase stores metadata/labels/eval
-- results ONLY; media + scene index live in VideoDB and are referenced by id.
-- Migration ordering: extensions -> runs -> events (FK) -> eval_cases (FK).

-- ── Extensions ──
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector embeddings

-- ── runs ──
CREATE TABLE IF NOT EXISTS runs (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name           text NOT NULL,
    run_status          text NOT NULL
                        CHECK (run_status IN ('success', 'failure', 'in_progress')),
    app_version         text,
    capture_session_id  text,
    rtstream_id         text,
    started_at          timestamptz NOT NULL,
    ended_at            timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runs_task_status
    ON runs (task_name, run_status);
CREATE INDEX IF NOT EXISTS idx_runs_task_started
    ON runs (task_name, started_at DESC);

-- ── events ──
-- Scene-level events delivered via webhook (deduped before insert).
CREATE TABLE IF NOT EXISTS events (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        uuid NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    event_id      text NOT NULL,
    t_offset_s    numeric NOT NULL,
    channel       text CHECK (channel IN ('display', 'mic')),
    description   text,
    template_tag  text
                  CHECK (template_tag IN
                         ('unexpected_modal', 'stuck_spinner', 'auth_failure')),
    embedding     vector,
    raw           jsonb,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_events_run_event UNIQUE (run_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_events_run_offset
    ON events (run_id, t_offset_s);

-- ivfflat on embedding (pgvector). 1536 dims; cosine ops. Build only when the
-- embedding dimensionality is known/populated by MEMORY; the index is created
-- lazily there to avoid an empty-table ivfflat warning. Documented intent:
--   CREATE INDEX idx_events_embedding ON events
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── eval_cases ──
CREATE TABLE IF NOT EXISTS eval_cases (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name           text NOT NULL,
    success_run_id      uuid REFERENCES runs (id) ON DELETE SET NULL,
    failure_run_id      uuid REFERENCES runs (id) ON DELETE SET NULL,
    human_divergence_s  numeric NOT NULL,
    query_text          text,
    expected_shot_ids   text[],
    notes               text,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_cases_task
    ON eval_cases (task_name);
