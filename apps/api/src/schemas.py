"""Pydantic request/response models mirroring docs/api-contracts.md.

Kept in sync with packages/types/src/index.ts (the TS mirror for apps/web).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

RunStatus = Literal["success", "failure", "in_progress"]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


# ── Sessions (Phase 1) ──
class SessionStartRequest(BaseModel):
    task_name: str
    run_status: RunStatus = "in_progress"
    app_version: Optional[str] = None


class SessionStartResponse(BaseModel):
    run_id: str
    capture_session_id: str
    client_token: str
    expires_at: str


class SessionEndRequest(BaseModel):
    run_status: Literal["success", "failure"]


class SessionEndResponse(BaseModel):
    run_id: str
    rtstream_id: str
    ended_at: str


# ── Search (Phase 1 — kill-criterion) ──
class SearchRequest(BaseModel):
    run_id: str
    query: str
    k: int = 3


class Shot(BaseModel):
    shot_id: str
    t_start_s: float
    t_end_s: float
    score: float
    description: str
    clip_url: str


class SearchResponse(BaseModel):
    shots: list[Shot]
    returned_shot_count: int
    e2e_latency_ms: int


# ── Compare (Phase 2) ──
class CompareRequest(BaseModel):
    success_run_id: Optional[str] = None
    failure_run_id: Optional[str] = None
    window_s: int = 10


class DivergenceEventIds(BaseModel):
    success: str
    failure: str


class CompareResponse(BaseModel):
    task_name: str
    divergence_timestamp: float
    failed_clip_url: str
    success_clip_url: str
    explanation: Optional[str] = None
    divergence_event_ids: DivergenceEventIds


# ── Webhooks ──
class WebhookAck(BaseModel):
    received: bool = True


# ── Health ──
class HealthzResponse(BaseModel):
    status: str
    replay_mode: bool
    videodb: str
    redis: str
    supabase: str
