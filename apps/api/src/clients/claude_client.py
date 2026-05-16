"""Anthropic Claude client wrapper.

Claude is invoked ONLY in the explanation layer (architecture.md), with an 8s
hard timeout from config and a template fallback (owned by the CLAUDE agent).
This wrapper just constructs the client with model + timeout from config — it
makes NO calls at scaffold time.
"""

from __future__ import annotations

from typing import Any

from ..config import get_settings
from ..logging import get_logger

log = get_logger("afr.claude")

_client: Any | None = None


def get_claude() -> Any:
    """Process-wide Anthropic client with the configured per-request timeout.

    Model name lives in ``settings.CLAUDE_MODEL``; callers pass it explicitly to
    ``messages.create(model=...)``. Timeout is ``settings.CLAUDE_TIMEOUT_S``.
    """
    global _client
    if _client is not None:
        return _client

    import anthropic

    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    _client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.CLAUDE_TIMEOUT_S,
    )
    log.info(
        "claude_client_created",
        model=settings.CLAUDE_MODEL,
        timeout_s=settings.CLAUDE_TIMEOUT_S,
    )
    return _client


def model_name() -> str:
    """The configured Claude model id."""
    return get_settings().CLAUDE_MODEL
