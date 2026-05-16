"""Structured logging — structlog JSON to stdout.

PLAN.md observability mandate: every request logs the full field set. This
module configures structlog and exposes helpers to bind those fields onto the
context-local logger so downstream agents (CAPTURE/INDEX/MEMORY/EVIDENCE/
CLAUDE/RELIABILITY) just call ``log_context(...)`` and ``get_logger()``.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

# The non-negotiable observability field set (PLAN.md).
OBSERVABILITY_FIELDS: tuple[str, ...] = (
    "capture_session_id",
    "rtstream_id",
    "task_name",
    "run_id",
    "query_text",
    "returned_shot_count",
    "relevance_scores",
    "compile_job_duration_ms",
    "webhook_dedupe_hit",
    "claude_token_count",
    "e2e_latency_ms",
)


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog to emit JSON to stdout. Idempotent."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "afr") -> structlog.stdlib.BoundLogger:
    """Return a bound logger."""
    return structlog.get_logger(name)


def bind_observability(**fields: Any) -> None:
    """Bind any subset of the mandated observability fields to the
    context-local logger so they ride along on every subsequent log line
    within the same request/task context.

    Unknown keys are allowed (forward-compat) but the canonical set is
    ``OBSERVABILITY_FIELDS``.
    """
    structlog.contextvars.bind_contextvars(**fields)


def clear_observability() -> None:
    """Clear the context-local observability bindings (call per request end)."""
    structlog.contextvars.clear_contextvars()


def new_observability_context(**fields: Any) -> None:
    """Reset then seed the observability context for a fresh request/task."""
    clear_observability()
    if fields:
        bind_observability(**fields)
