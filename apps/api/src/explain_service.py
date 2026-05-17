"""Claude divergence explanation (Wave 4 — CLAUDE).

`GET /tasks/{task_name}/explain?query=...` → SSE. Claude is used HERE ONLY
(architecture rule). The static system + instruction prefix is prompt-cached
(cache_control) so repeat structurally-identical calls are cheap; the full
rendered answer is also cached in Redis on `(task_name, normalized_query)` for
`REDIS_DEMO_CACHE_TTL_S` so a repeat query replays instantly. An 8s hard
timeout falls back to a deterministic template explanation — the UI never
hard-fails (api-contracts.md / phase-4-claude.md).

SSE event shapes mirror packages/types `ExplainEvent`:
  token: {"type":"token","text": "..."}
  done:  {"type":"done","cached": bool,"claude_token_count": int}
  error: {"type":"error","message": "..."}
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import AsyncIterator

from . import memory_router
from .clients import claude_client
from .config import get_settings
from .logging import bind_observability, get_logger

log = get_logger("afr.explain")

# Verbatim from MASTER (phase-4-claude.md) — kept static so it prompt-caches.
SYSTEM_PROMPT = (
    "You are a forensic agent analyst. Given two event sequences (one "
    "successful, one failed) and the identified divergence point, explain in "
    "2-3 sentences what went wrong and why. Cite specific timestamped evidence. "
    "Do not speculate beyond the provided events."
)

_CACHE_PREFIX = "afr:explain:"


def _norm(q: str) -> str:
    return " ".join(q.lower().split())


def _cache_key(task_name: str, query: str) -> str:
    h = hashlib.sha256(f"{task_name}|{_norm(query)}".encode()).hexdigest()[:32]
    return f"{_CACHE_PREFIX}{h}"


def _fmt_seq(events: list[dict]) -> str:
    return "\n".join(
        f"  T+{float(e['t_offset_s']):06.2f}s [{e['event_id']}] {e['description']}"
        for e in events
    )


def _build_user_prompt(task_name: str, s_events, f_events, div) -> str:
    return (
        f"Task: {task_name}\n\n"
        f"SUCCESSFUL run events:\n{_fmt_seq(s_events)}\n\n"
        f"FAILED run events:\n{_fmt_seq(f_events)}\n\n"
        f"Identified first divergence: T+{div.divergence_timestamp:.2f}s "
        f"(successful event {div.success_event_id} vs failed event "
        f"{div.failure_event_id}; semantic similarity "
        f"{div.similarity_at_divergence:.2f}).\n\n"
        "Explain what went wrong and why, citing timestamps like T+15.00s."
    )


def _template_fallback(task_name: str, s_events, f_events, div) -> str:
    f_at = next(
        (e for e in f_events if e["event_id"] == div.failure_event_id), None
    )
    s_at = next(
        (e for e in s_events if e["event_id"] == div.success_event_id), None
    )
    later = next(
        (e for e in f_events if e.get("template_tag") == "auth_failure"), None
    )
    parts = [
        f"The runs were identical until T+{div.divergence_timestamp:.2f}s, where "
        f"the failed run diverged: \"{(f_at or {}).get('description', 'n/a')}\" "
        f"versus the successful run's \"{(s_at or {}).get('description', 'n/a')}\"."
    ]
    if later:
        parts.append(
            f"This led to the failure at T+{float(later['t_offset_s']):.2f}s: "
            f"{later['description']}"
        )
    return " ".join(parts)


async def _stream_claude(system, user) -> AsyncIterator[str]:
    """Yield text deltas from Claude with prompt caching on the system prefix."""
    client = claude_client.get_claude()
    model = claude_client.model_name()

    def _run():
        chunks: list[str] = []
        with client.messages.stream(
            model=model,
            max_tokens=400,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
            final = stream.get_final_message()
        usage = getattr(final, "usage", None)
        tokens = (getattr(usage, "input_tokens", 0) or 0) + (
            getattr(usage, "output_tokens", 0) or 0
        )
        return chunks, tokens

    chunks, tokens = await asyncio.to_thread(_run)
    for c in chunks:
        yield c
    yield f"\x00TOKENS:{tokens}"  # sentinel: token count rides out-of-band


def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps({'type': event_type, **payload})}\n\n"


async def explain_stream(task_name: str, query: str) -> AsyncIterator[str]:
    """The SSE generator backing the endpoint."""
    settings = get_settings()
    bind_observability(task_name=task_name, query_text=query)
    key = _cache_key(task_name, query)

    # 1. Redis cache hit → replay instantly.
    try:
        from .clients.redis_client import get_redis

        cached = await get_redis().get(key)
        if cached:
            log.info("explain_cache_hit", task_name=task_name)
            for tok in json.loads(cached)["text_chunks"]:
                yield _sse("token", {"text": tok})
            yield _sse("done", {"cached": True, "claude_token_count": 0})
            return
    except Exception as exc:  # noqa: BLE001 — cache is best-effort
        log.warning("explain_cache_read_failed", error=str(exc)[:160])

    # 2. Build prompt from PROVIDED events only (no hallucinated events).
    s_events, f_events, div = memory_router.event_sequences(task_name)
    user_prompt = _build_user_prompt(task_name, s_events, f_events, div)

    full_text: list[str] = []
    token_count = 0
    used_fallback = False

    try:
        agen = _stream_claude(SYSTEM_PROMPT, user_prompt)

        async def _next():
            return await agen.__anext__()

        while True:
            try:
                piece = await asyncio.wait_for(
                    _next(), timeout=settings.CLAUDE_TIMEOUT_S
                )
            except StopAsyncIteration:
                break
            if piece.startswith("\x00TOKENS:"):
                token_count = int(piece.split(":", 1)[1])
                continue
            full_text.append(piece)
            yield _sse("token", {"text": piece})
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        # 3. Timeout / instability → deterministic template (never hard-fail).
        used_fallback = True
        log.warning("explain_fallback", task_name=task_name, error=str(exc)[:160])
        if not full_text:
            fb = _template_fallback(task_name, s_events, f_events, div)
            full_text = [fb]
            yield _sse("error", {"message": "claude_unavailable_template_fallback"})
            yield _sse("token", {"text": fb})

    bind_observability(claude_token_count=token_count)
    log.info(
        "explain_done",
        task_name=task_name,
        claude_token_count=token_count,
        fallback=used_fallback,
    )

    # 4. Cache the rendered answer for instant replay.
    try:
        from .clients.redis_client import get_redis

        await get_redis().set(
            key,
            json.dumps({"text_chunks": full_text}),
            ex=settings.REDIS_DEMO_CACHE_TTL_S,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("explain_cache_write_failed", error=str(exc)[:160])

    yield _sse("done", {"cached": False, "claude_token_count": token_count})
