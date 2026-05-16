"""Eval suite runner — OWNED BY THE `RELIABILITY` AGENT.

Responsibility (architecture.md): run the eval suite over labeled test pairs in
`apps/api/evals/` against the `eval_cases` table (data-model.md) — precision@3
on `query_text`/`expected_shot_ids`, divergence error vs `human_divergence_s`.

Spec: docs/specs/phase-5-reliability.md
TODO(RELIABILITY): implement; this scaffold intentionally contains no logic.
"""

from __future__ import annotations
