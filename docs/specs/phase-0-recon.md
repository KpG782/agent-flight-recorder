# Phase 0 — Recon

**Objective:** Gather authoritative VideoDB API knowledge, avoid saturated demo
framings, and lock the UI direction before any code.

**Inputs / preconditions:** `.env` filled; `MASTER.md`, `docs/PLAN.md`,
`docs/architecture.md` available. No code exists yet.

**Parallel agent assignments (Wave 0 — all 3 concurrent):**
- `RECON-A` → `docs/videodb-cheatsheet.md` (fill the placeholder per its checklist).
  Use context7 MCP if available, else WebFetch on https://docs.videodb.io.
- `RECON-B` → `docs/saturated-patterns.md`. Crawl https://videodb.io/showcase and
  https://notebooks.videodb.io; list what's already built so README/demo narrative
  explicitly avoids those framings.
- `RECON-C` → UI brief appended to `specs/phase-3-ui.md`. Invoke `ui-ux-pro-max`;
  propose the split-pane forensic UI (failed pane | success pane | prompt bar |
  divergence timeline). "Calm forensic tool" aesthetic, dark mode primary.

**Concrete tasks:** each agent produces its single markdown deliverable, copy-pasteable
SDK signatures for RECON-A, concrete component references (shadcn) for RECON-C.

**Acceptance criteria:** all three deliverables exist and are complete (no stubs);
`videodb-cheatsheet.md` covers all 12 checklist items with exact signatures.

**Gate / exit:** Orchestrator synthesizes the three outputs into `docs/PLAN.md`
(skill-substitution note already recorded) and the affected phase specs. Only then
dispatch Wave 1.

**Risks:** context7 MCP absent → WebFetch fallback (slower, fine); showcase site
structure changes → capture whatever is reachable, note gaps.
