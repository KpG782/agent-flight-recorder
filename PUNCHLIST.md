# PUNCHLIST — needs a human (read first when you return)

> Autonomous build status: **Waves 1–4 + demo polish complete and verified in
> `REPLAY_MODE`.** The killshot flow works end-to-end with zero external
> dependencies. Everything below needs your physical presence, credentials, or a
> decision. Ordered by demo-criticality. Deadline: **2026-05-18 12:30 PM Manila**.

## ✅ What works right now (no action needed)

- `REPLAY_MODE=true` killshot: `/search`, `/compare` (divergence = **15.00s,
  0.00s error**), `/explain` (real Claude SSE, cited, Redis cache-hit on
  repeat), `/webhooks/videodb` (fast ack + dedupe), `WS /ws` event feed.
- Next.js UI builds clean (`next build` ✓), typechecks ✓, routes `/` →
  `/runs/demo_login_flow/compare`.
- Eval suite: 10 cases, top-1 0.90, recall@3 0.78 — `apps/api/evals/results.md`.
- README (7 sections) + this file. Local commit made; **not pushed**.

## 🔴 P0 — blocks the *live* path (demo is fine without these via REPLAY)

1. **✅ RESOLVED — `DATABASE_URL` live.** Supabase Postgres now connects via the
   pooler; `migrations/apply.py` applied `0001_init.sql` + `0002_seed_demo.sql`
   (runs=2, events=14, eval_cases=10). `/healthz` is all-ok with
   `replay_mode:false`; `/compare`, `/search`, `/explain` verified end-to-end
   against live Supabase. Root causes fixed: (a) pasted trailing label was
   corrupting the value; (b) `asyncpg`'s DSN-string parser mishandled a
   URL-special char in the password — `pg_pool()` now connects via explicit
   parsed components + `statement_cache_size=0` for the PgBouncer pooler.
   _Historical detail below, kept for reference:_

   <details><summary>original diagnosis</summary>
   The DSN is now correct: pooler user `postgres.pospouafsajrwyfygbxx`, host
   `aws-1-ap-northeast-1.pooler.supabase.com:6543`, db `postgres` (a pasted
   trailing label that was corrupting the value has been stripped; `?pgbouncer=true`
   removed — asyncpg handles the pooler via `statement_cache_size=0` in code).
   It still fails `password authentication failed for user "postgres"`, which
   with a well-formed pooler DSN means **the 15-char password is wrong**
   (Supabase's pooler always collapses the reported user to bare `postgres`).
   **Action:** Supabase Dashboard → Project Settings → Database → either copy
   the exact **Connection pooler** URI or **Reset database password**, then put
   ONLY the URL on the `DATABASE_URL=` line (no quotes, no trailing label —
   keep labels on their own `#` comment line). Then
   `cd apps/api && .venv/bin/python migrations/apply.py` (applies
   `0001_init.sql` + `0002_seed_demo.sql`). Until then the fixture fallback
   (`ALLOW_FIXTURE_FALLBACK`) carries every read path — demo unaffected.
   ⚠️ The `.env` line was fixed via tooling; **don't re-save `.env` from the
   IDE** or the stale buffer will clobber it (paste the corrected URL in the
   IDE instead, or close the file first).
   </details>

2. **Record the two real demo runs.** The clip URLs are placeholder seekable
   MP4s (Google sample videos) — the scrub / marker / explanation are all real,
   but the *video content* is not the actual login flow. You need to:
   - Screen-capture a scripted **success** login and a **mistyped-password
     failure** on a clean demo SaaS app (large buttons, clear text).
   - Export each run's display RTStream from VideoDB.
   - Put the two stream URLs into `.env` as `REPLAY_SUCCESS_CLIP_URL` /
     `REPLAY_FAILURE_CLIP_URL` (overrides the fixture; no code change).
   This is the only thing standing between "flow works" and "demo is real".

## 🟠 P1 — needed for the live capture / durable path

3. **macOS capture permissions.** Live (non-`REPLAY`) capture needs Screen
   Recording + Microphone granted to the VideoDB capture binary. The Phase-1
   kill-gate *live* verification was deferred per your instruction — if you want
   to run it for real, grant perms, restart, and exercise
   `POST /sessions/start` → capture client → `/search` 3×.

4. **ngrok for webhooks.** `ngrok http 8000`, set `WEBHOOK_BASE_URL=https://<sub>.ngrok-free.app`.
   The handler is verified locally (ack + Redis dedupe + DB backstop) but not
   against real VideoDB Cloud delivery.

## 🟡 P2 — submission ritual (your call)

5. **Replay 3× green, then record the ≤90s demo video.** Opening 15s must be the
   killshot (not "watch me capture my screen" — saturated framing, RECON-B).
   REPLAY is verified working; the 3× pre-record ritual + the recording itself
   are yours.

6. **Push public + submit.** Commits are **local only** (no push, per your build
   prefs). `git push` when ready and fill the submission form before the
   deadline. Verify `.env` is git-ignored (it is) before pushing.

## Notes / decisions made autonomously (flag if you disagree)

- **No shadcn CLI / TanStack Query / lucide.** Hand-rolled square forensic UI
  primitives + React state + native fetch/EventSource/WebSocket. Rationale:
  zero extra npm deps = a demo that can't fail on `pnpm install`; the styling
  contract (the RECON-C brief) is met. Reversible if you want the CLI set.
- **Stdlib similarity scorer, not embeddings.** Justified in README §4 (no
  vector dep; deterministic for the demo corpus). pgvector column reserved.
- **`CLAUDE_MODEL=claude-sonnet-4-6`** (spec says Sonnet) — verified streaming.
- Clip placeholders are Google sample MP4s (seekable, stable, public).
