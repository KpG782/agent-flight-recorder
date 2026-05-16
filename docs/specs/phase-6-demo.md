# Phase 6 — Demo + Submission

**Objective:** Ship: 90-second demo video, complete README, eval suite with real
numbers, public repo, submission form filled.

**Inputs / preconditions:** Phase-5 gate PASSED (REPLAY_MODE green 3×).

**Parallel agent assignments (Wave 5 — 2 concurrent):**
- `EVAL`: `incident_evaluator.py` + 10 labeled test pairs in `apps/api/evals/`
  (`eval_cases` table). Measure: **retrieval precision@3**, **time-to-first-evidence
  (ms)**, **divergence accuracy** (within 5s of human label). Emit a markdown table.
- (Orchestrator/inline): record the 90-second demo video — **opening 15s must show the
  killshot**; author README.

**Concrete tasks — README sections (all required):**
1. Problem
2. Architecture diagram (from `architecture.md`)
3. VideoDB primitives used — list all 6 (from `PLAN.md`)
4. Eval methodology + numbers (table from `EVAL`)
5. Cost model (1 frame/5s rationale; ~$2–5 per 10-min capture; 200+ session headroom)
6. Failure modes + mitigations (table from MASTER risk matrix)
7. How to run locally (`.env` from `.env.example`, Upstash Redis, ngrok, REPLAY_MODE)

**Acceptance criteria:** demo video ≤90s with killshot in first 15s; README has all 7
sections; eval table shows real measured numbers for all 3 metrics; repo is public.

**Gate / exit:** public GitHub repo pushed + submission form filled before
2026-05-18 12:30 PM Manila. Done.

**Risks:** running over time (REPLAY_MODE keeps demo deterministic; record early);
thin eval set (10 pairs minimum, reuse `demo_login_flow` variants); last-minute repo
secrets leak (verify `.env` git-ignored, scrub keys from any committed example).
