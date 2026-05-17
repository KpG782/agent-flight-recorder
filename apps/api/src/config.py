"""Application configuration.

pydantic-settings ``Settings`` that reads the EXACT env var names mandated by
the Wave 0 recon (see docs/PLAN.md). Names are case-insensitive but must match
``.env`` exactly. Loaded from the repo-root ``.env``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is three levels up from this file: src/ -> apps/api/ -> apps/ -> root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    """All runtime config. Field names == exact .env var names (Wave 0)."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── VideoDB ──
    VIDEO_DB_API_KEY: str = ""
    VIDEO_DB_BASE_URL: str = "https://api.videodb.io"

    # ── Anthropic (Claude — explanation layer only) ──
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_TIMEOUT_S: float = 8.0

    # ── Supabase ──
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = ""

    # ── Redis (Upstash, TLS rediss://) ──
    REDIS_URL: str = ""
    REDIS_IDEMPOTENCY_TTL_S: int = 86400
    REDIS_DEMO_CACHE_TTL_S: int = 3600

    # ── Webhooks / public ingress ──
    WEBHOOK_BASE_URL: str = ""
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # ── App config ──
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    REPLAY_MODE: bool = False
    DEMO_TASK_NAME: str = "demo_login_flow"
    CAPTURE_FRAME_INTERVAL_S: int = 5

    # ── Replay fallback (the demo's safety net) ──
    # REPLAY_MODE serves a fully pre-indexed run pair from a local JSON fixture
    # so the killshot demo has ZERO external dependencies (no VideoDB live, no
    # Supabase, no network) — "the demo cannot fail" (phase-5-reliability.md).
    # The fixture also seeds Supabase via migrations/0002 when the DB is live.
    REPLAY_FIXTURE_PATH: str = ""  # default resolved to apps/api/fixtures/demo_login_flow.json
    # Placeholder clip URLs (seekable public MP4s) until the two real demo runs
    # are screen-captured + exported from VideoDB (see PUNCHLIST.md).
    REPLAY_SUCCESS_CLIP_URL: str = (
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"
    )
    REPLAY_FAILURE_CLIP_URL: str = (
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
    )
    # Divergence detection: first aligned scene pair whose semantic similarity
    # drops below this is "where it first diverged" (memory_router).
    MEMORY_DIVERGENCE_THRESHOLD: float = 0.6

    # When the live Supabase Postgres is unreachable (e.g. DATABASE_URL not yet
    # fixed), allow the fixture to back read paths so the build stays runnable.
    ALLOW_FIXTURE_FALLBACK: bool = True

    # ── Web (browser-exposed; carried for completeness) ──
    NEXT_PUBLIC_API_BASE_URL: str = "http://localhost:8000"
    NEXT_PUBLIC_WS_URL: str = "ws://localhost:8000/ws"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide singleton Settings."""
    return Settings()
