# Continuation — Agent Flight Recorder (resume here)

> ⚠️ **SUPERSEDED 2026-05-17 by the autonomous build.** Waves 1–4 + demo
> polish are complete and verified in `REPLAY_MODE`. The current handoff is
> **`/PUNCHLIST.md`** (read that first), then `/README.md`. The text below is
> the pre-build state, kept for history only.

> Handoff written 2026-05-17. Read this + `docs/PLAN.md` first to resume.
> Hackathon deadline: **2026-05-18, 12:30 PM Manila**. Solo build.

## TL;DR — exact cursor

At the **start of Wave 1**. The next action is building the backend/monorepo
scaffold. Wave 0 (recon) is complete and synthesized. **No app code exists yet;
the repo is NOT a git repo; nothing has been committed or pushed.**

## State of the world

**Done**
- All `docs/` specs written: `PLAN.md`, `orchestration.md`, `architecture.md`,
  `data-model.md`, `api-contracts.md`, `videodb-cheatsheet.md`, `specs/phase-0..6`.
- `.gitignore`, `.env.example` (blank template), `.env` (real keys, see below).
- **Wave 0 recon ran (3 parallel agents) and was synthesized:**
  - `videodb-cheatsheet.md` — verified SDK signatures from `videodb-python` source.
  - `saturated-patterns.md` — positioning; our two-run divergence lane is uncontested.
  - UI brief filled into `specs/phase-3-ui.md`.
  - 3 corrections folded into `PLAN.md` ("Wave 0 recon — confirmed corrections")
    and `api-contracts.md`.
- Installed skills (this machine): `.agents/skills/supabase` and
  `.agents/skills/supabase-postgres-best-practices` (symlinked to Claude Code).
  Use these for the Supabase migration / Postgres work in Wave 1.

**Not done**
- Wave 1: `BE-SCAFFOLD` → then `CAPTURE` + `INDEX` → Phase 1 kill-criterion gate.
- Waves 2–5.

## Wave 0 corrections (authoritative — supersede MASTER.md)

1. **Env var is `VIDEO_DB_API_KEY`** (not `VIDEODB_API_KEY`); also `VIDEO_DB_BASE_URL`.
   Already fixed in `.env`/`.env.example`. SDK install: `pip install "videodb[capture,websockets]"`.
2. **VideoDB primitive #2 reframed:** no SDK call for per-scene custom tags. Use
   `CaptureSession(metadata=...)` + Supabase `runs`/`events` correlation.
3. **No webhook HMAC exists.** Trust = secret ngrok URL + `event_id` dedupe.
   `/search` & `/compare` must use semantic `RTStream.search` (collection keyword
   search raises `NotImplementedError`). Normalize event timestamps to seconds on ingest.

## `.env` status

| Var | Status |
|---|---|
| `VIDEO_DB_API_KEY`, `ANTHROPIC_API_KEY` | ✅ set |
| `SUPABASE_URL` / `_ANON_KEY` / `_SERVICE_ROLE_KEY` | ✅ set |
| `REDIS_URL` (Upstash, `rediss://`) | ✅ set |
| `DATABASE_URL` | ⚠️ real password, but **DIRECT endpoint** (`db.<ref>.supabase.co:5432`). Likely needs `?sslmode=require` or the **pooler** (`aws-0-<region>.pooler.supabase.com:6543`, user `postgres.<ref>`). Test before relying on it. |
| `WEBHOOK_BASE_URL` | ⬜ empty — not needed until Phase 5 |

⚠️ Do **not** edit `.env` in the IDE while an agent is also writing it — the editor
buffer clobbered keys twice. Edit single lines via tooling, or close it in the IDE.

## Open question to resolve before resuming

The `BE-SCAFFOLD` dispatch was **interrupted by the user twice** at the same point.
The cause was never stated. **Before re-dispatching, ask the user which they want:**
- Review `docs/` specs themselves first?
- Scaffold built inline in small approve-as-you-go steps (not one big agent)?
- A narrower scaffold (monorepo skeleton only → review → then DB migration)?
- Just not ready to build yet?

## Confirmed build preferences (apply without re-asking)

- Git: `git init` + commit, **single-line** commit message, **do NOT push**.
  Commit message trailer required: `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`.
- Pace: **scaffold only, then STOP and report** — do not chain into CAPTURE/INDEX
  without an explicit go.
- Check in with the user before large sub-agent dispatches and before commits.

## Resume procedure

1. Read `docs/PLAN.md` (esp. Wave 0 corrections) + `docs/orchestration.md`.
2. Ask the user the open question above; get an explicit go.
3. Execute Wave 1 scaffold per `specs/phase-1-kill-gate.md`, using the installed
   `supabase` / `supabase-postgres-best-practices` skills for the migration.
   Exact env names, `videodb[capture,websockets]`, Redis TLS, `/healthz` pinging all 3.
4. Verify (uvicorn boots, `/healthz` ok, 3 tables exist), one local commit, no push.
5. STOP, report, await go for CAPTURE + INDEX.
6. Phase 1 = HARD kill-criterion gate: 30s capture → indexed events → NL search →
   timestamped clip. FAIL ⇒ stop, contact user, propose Demo Truth Auditor pivot.

## Pointers

- Master spec: `MASTER.md` (read-only). Synthesized plan: `docs/PLAN.md`.
- Orchestration waves/agents: `docs/orchestration.md`.
- Approved plan file: `/Users/kuya/.claude/plans/great-now-try-to-melodic-neumann.md`.
