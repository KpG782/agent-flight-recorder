/**
 * @afr/types — shared TypeScript types mirroring docs/api-contracts.md
 * response shapes. Single source of truth between apps/api (FastAPI) and
 * apps/web (Next.js). Keep in sync with apps/api/src/schemas.py.
 */

export type RunStatus = "success" | "failure" | "in_progress";
export type Channel = "display" | "mic";
export type TemplateTag =
  | "unexpected_modal"
  | "stuck_spinner"
  | "auth_failure"
  | null;

/** Standard error envelope: all API errors use this shape. */
export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

/* ── Sessions (Phase 1) ─────────────────────────────────────────── */

export interface SessionStartRequest {
  task_name: string;
  run_status: RunStatus;
  app_version?: string;
}

export interface SessionStartResponse {
  run_id: string;
  capture_session_id: string;
  client_token: string;
  expires_at: string;
}

export interface SessionEndRequest {
  run_status: Extract<RunStatus, "success" | "failure">;
}

export interface SessionEndResponse {
  run_id: string;
  rtstream_id: string;
  ended_at: string;
}

/* ── Search (Phase 1 — kill-criterion) ──────────────────────────── */

export interface SearchRequest {
  run_id: string;
  query: string;
  k?: number;
}

export interface Shot {
  shot_id: string;
  t_start_s: number;
  t_end_s: number;
  score: number;
  description: string;
  clip_url: string;
}

export interface SearchResponse {
  shots: Shot[];
  returned_shot_count: number;
  e2e_latency_ms: number;
}

/* ── Compare (Phase 2) ──────────────────────────────────────────── */

export interface CompareRequest {
  success_run_id?: string;
  failure_run_id?: string;
  window_s?: number;
}

export interface CompareResponse {
  task_name: string;
  divergence_timestamp: number;
  failed_clip_url: string;
  success_clip_url: string;
  explanation: string | null;
  divergence_event_ids: {
    success: string;
    failure: string;
  };
}

/* ── Explanation (Phase 4 — SSE) ────────────────────────────────── */

export interface ExplainTokenEvent {
  type: "token";
  text: string;
}

export interface ExplainDoneEvent {
  type: "done";
  cached: boolean;
  claude_token_count: number;
}

export interface ExplainErrorEvent {
  type: "error";
  message: string;
}

export type ExplainEvent =
  | ExplainTokenEvent
  | ExplainDoneEvent
  | ExplainErrorEvent;

/* ── Webhooks (Phase 5) ─────────────────────────────────────────── */

export interface WebhookAck {
  received: true;
}

/* ── WebSocket (Phase 3/5) ──────────────────────────────────────── */

export interface WsEventFrame {
  type: "event";
  run_id: string;
  t_offset_s: number;
  description: string;
  template_tag: TemplateTag;
}

/* ── Health ─────────────────────────────────────────────────────── */

export type HealthState = "ok" | "error" | "skipped";

export interface HealthzResponse {
  status: "ok" | "degraded";
  replay_mode: boolean;
  videodb: HealthState | string;
  redis: HealthState | string;
  supabase: HealthState | string;
}
