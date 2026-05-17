"""Eval suite runner (Wave 5 — EVAL).

Measures three metrics over the labeled `eval_cases` (fixture or Supabase):
- **retrieval precision@3** — of the top-3 shots `/search` returns for a
  case's `query_text`, the fraction that are in `expected_shot_ids`.
- **time-to-first-evidence (ms)** — `/compare` end-to-end latency (divergence +
  two playable clips = the first usable forensic evidence).
- **divergence accuracy** — `|computed_divergence − human_divergence_s|`;
  "accurate" if within 5s of the human label.

Emits a markdown table to stdout and `apps/api/evals/results.md`.
Run: `REPLAY_MODE=true .venv/bin/python -m src.incident_evaluator`
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

from . import memory_router, replay_store, store
from .logging import configure_logging, get_logger
from .schemas import CompareRequest, SearchRequest
from .search_service import search

log = get_logger("afr.eval")

_ACCURACY_TOLERANCE_S = 5.0
_RESULTS_MD = Path(__file__).resolve().parent.parent / "evals" / "results.md"


def _precision_at_3(got_ids: list[str], expected: list[str]) -> float:
    if not got_ids:
        return 0.0
    top = got_ids[:3]
    hits = sum(1 for g in top if g in set(expected))
    return hits / min(3, len(top))


def _recall_at_3(got_ids: list[str], expected: list[str]) -> float:
    """Fraction of the labeled relevant shots found in the top-3. With sparse
    (often single) ground truth this reflects retrieval quality more faithfully
    than p@3 (whose ceiling is |expected|/3)."""
    if not expected:
        return 0.0
    found = sum(1 for e in set(expected) if e in set(got_ids[:3]))
    return found / len(set(expected))


def run_eval() -> dict:
    cases = replay_store.eval_cases()
    task = replay_store.fixture_task_name()
    _, failure = store.get_run_pair(task)

    rows: list[dict] = []
    precisions: list[float] = []
    recalls: list[float] = []
    top1_hits = 0

    for ec in cases:
        t0 = time.perf_counter()
        res = search(
            SearchRequest(run_id=failure["id"], query=ec["query_text"], k=3)
        )
        ms = (time.perf_counter() - t0) * 1000
        got = [s.shot_id for s in res.shots]
        p3 = _precision_at_3(got, ec["expected_shot_ids"])
        r3 = _recall_at_3(got, ec["expected_shot_ids"])
        top1 = bool(got and got[0] in set(ec["expected_shot_ids"]))
        top1_hits += top1
        precisions.append(p3)
        recalls.append(r3)
        rows.append(
            {
                "query": ec["query_text"],
                "expected": ",".join(ec["expected_shot_ids"]),
                "got_top3": ",".join(got[:3]),
                "p@3": p3,
                "top1": top1,
                "search_ms": round(ms, 1),
            }
        )

    # Divergence accuracy + time-to-first-evidence (the /compare path).
    t0 = time.perf_counter()
    div = memory_router.find_divergence(task)
    ttfe_ms = (time.perf_counter() - t0) * 1000
    human = float(cases[0]["human_divergence_s"]) if cases else 0.0
    div_err = abs(div.divergence_timestamp - human)
    div_accurate = div_err <= _ACCURACY_TOLERANCE_S

    summary = {
        "n_cases": len(cases),
        "mean_precision_at_3": round(statistics.mean(precisions), 3) if precisions else 0.0,
        "mean_recall_at_3": round(statistics.mean(recalls), 3) if recalls else 0.0,
        "top1_accuracy": round(top1_hits / len(cases), 3) if cases else 0.0,
        "mean_search_ms": round(
            statistics.mean(r["search_ms"] for r in rows), 1
        )
        if rows
        else 0.0,
        "time_to_first_evidence_ms": round(ttfe_ms, 1),
        "divergence_error_s": round(div_err, 2),
        "divergence_accurate_within_5s": div_accurate,
        "rows": rows,
    }
    return summary


def to_markdown(s: dict) -> str:
    lines = [
        "# Agent Flight Recorder — Eval Results",
        "",
        f"Cases: **{s['n_cases']}** · task `demo_login_flow` "
        "(success vs. mistyped-password failure).",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Retrieval precision@3 (mean) | **{s['mean_precision_at_3']:.3f}** "
        "(ceiling ≈0.33 — most cases have a single relevant shot) |",
        f"| Retrieval recall@3 (mean) | **{s['mean_recall_at_3']:.3f}** |",
        f"| Top-1 retrieval accuracy | **{s['top1_accuracy']:.3f}** |",
        f"| Time-to-first-evidence (`/compare`) | **{s['time_to_first_evidence_ms']:.1f} ms** |",
        f"| Mean `/search` latency | {s['mean_search_ms']:.1f} ms |",
        f"| Divergence error vs. human label | **{s['divergence_error_s']:.2f} s** |",
        f"| Divergence accurate (≤5s) | **{'yes' if s['divergence_accurate_within_5s'] else 'no'}** |",
        "",
        "## Per-case retrieval",
        "",
        "| Query | Expected | Top-3 returned | P@3 | Top-1 |",
        "|---|---|---|---|---|",
    ]
    for r in s["rows"]:
        lines.append(
            f"| {r['query']} | `{r['expected']}` | `{r['got_top3']}` | "
            f"{r['p@3']:.2f} | {'✓' if r['top1'] else '·'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    configure_logging("WARNING")
    summary = run_eval()
    md = to_markdown(summary)
    _RESULTS_MD.parent.mkdir(parents=True, exist_ok=True)
    _RESULTS_MD.write_text(md + "\n")
    print(md)
    print(f"\n[written] {_RESULTS_MD}")


if __name__ == "__main__":
    main()
