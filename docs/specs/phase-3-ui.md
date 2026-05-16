# Phase 3 — Killshot UI

**Objective:** The split-pane forensic page where the killshot happens: user asks
"where did the failed run first diverge from the successful one?" → both videos scrub
to the divergence timestamp in sync → red timeline marker → explanation streams below.

**Inputs / preconditions:** Phase-2 gate PASSED; `/compare` live; `api-contracts.md`
frozen; RECON-C UI brief (appended below by Wave 0).

**Parallel agent assignments (Wave 3 — 2 concurrent):**
- `UI` (invoke `ui-ux-pro-max` + `vercel:shadcn` first): Next.js 15 App Router page at
  `/runs/[task]/compare`. Two `<video>` elements bound to a shared timeline state;
  shadcn/ui prompt bar + command palette (`Cmd+K`) + event rail. Tailwind dark theme,
  monospace timestamps, subtle red glow on the divergence marker, no rounded-corner
  SaaS friendliness — "Linear meets a flight black-box recorder".
- `API-INTEGRATION`: TanStack Query hooks for `/compare`; WebSocket client for live
  events (`WS /ws?run_id=`); SSE consumer for the explanation stream; optimistic state.

**Concrete tasks:** shared timeline store (current time, divergence time, play/pause);
seeking either video seeks both; divergence marker rendered from
`divergence_timestamp`; prompt bar submits the canonical question and triggers
`/compare` then the explanation SSE.

**Acceptance criteria:** entering the killshot query scrubs both `<video>` elements to
`divergence_timestamp` within ±0.5s of each other; red marker visible on the timeline;
page works in dark mode; no console errors.

**Gate / exit:** synchronized scrub-to-divergence demonstrated → dispatch Wave 4.

**Risks:** HLS clip seeking jitter (preload metadata, seek on `canplay`); WS reconnect
storms (backoff, dedupe by event_id); layout breaking on long descriptions (truncate +
tooltip).

---

## UI Design Brief (filled by `RECON-C` in Wave 0)

**Aesthetic thesis.** This is an instrument, not a SaaS product. The user is reading a
black box after a crash — every pixel should feel like calm, precise, deliberate
forensic equipment. Reference points: Linear's restraint + a flight-data-recorder
readout. Rule of thumb: if it looks friendly, it's wrong. Square it off, mute it down,
let the red marker be the only thing that shouts.

### 0. Global rules (apply everywhere)

- **Border radius:** `--radius: 2px` globally. Video panes, prompt bar, timeline track
  = `rounded-none` (0px). Only the `Cmd+K` command palette and tooltips may use 2px.
  No pill buttons, no soft cards. Override shadcn's default `--radius` to `0.125rem`.
- **Borders over shadows.** Separation is done with 1px hairline borders, never drop
  shadows. The only shadow in the app is the divergence-marker glow.
- **No gradients, no glass, no blur** (except an optional 1px scanline overlay at 3%
  opacity on video panes, `prefers-reduced-motion`-gated).
- **Density is a feature.** Tight spacing scale: 4 / 8 / 12 / 16 / 24 px. Section gaps
  are hairline rules, not whitespace.
- **Color is information.** Chrome is monochrome slate; green = the successful run,
  red = divergence/failed run. Nothing else is colored.
- **Motion is mechanical.** 150–220ms, `ease-out` on enter / `ease-in` on exit. The
  scrub-to-divergence is the single hero animation; everything else is near-instant.
  Honor `prefers-reduced-motion` (jump-cut instead of animated scrub).

### 1. Layout grid — 4 regions

Single full-viewport, non-scrolling shell (`h-dvh`, `overflow-hidden`) using CSS grid:

```
┌──────────────────────────── header (40px) ─────────────────────────────┐
│  AGENT FLIGHT RECORDER · task: demo_login_flow · REPLAY        ⌘K       │
├──────────────────────────────┬──────────────────────────────────────────┤
│                              │                                          │
│   FAILED RUN  (red label)    │   SUCCESSFUL RUN  (green label)          │
│   <video> pane               │   <video> pane                           │
│   1fr                        │   1fr                                     │
│                              │                                          │
├──────────────────────────────┴──────────────────────────────────────────┤
│  DIVERGENCE TIMELINE  — single shared track, red marker  (96px)          │
├───────────────────────────────────────────────────────────────────────────┤
│  PROMPT BAR  — canonical question input + streamed explanation (auto/240) │
└───────────────────────────────────────────────────────────────────────────┘
```

- **Grid template:** `grid-rows-[40px_minmax(0,1fr)_96px_auto]`, with the video row
  split `grid-cols-2` and a 1px vertical divider between panes
  (`divide-x divide-[--border]`). The whole shell is `grid` so the timeline + prompt
  bar are fixed furniture and never scroll out of view.
- **Proportions:** video row takes all remaining height (~60–70vh on a 1080p laptop);
  timeline fixed 96px; prompt/explanation region `auto`, capped `max-h-[240px]` with
  the explanation body internally scrollable (`overflow-y-auto`) so layout never breaks
  on long Claude output (spec risk: "layout breaking on long descriptions").
- **The two video panes are visually symmetric and equal width (50/50).** Symmetry is
  the point — the eye compares them. No featured/secondary sizing.
- **Responsive behavior:**
  - `≥1024px` (primary / demo target): side-by-side as drawn above.
  - `768–1023px`: panes stack vertically (`grid-cols-1`, failed on top), timeline +
    prompt bar stay pinned at the bottom; video row becomes scroll-internal if needed.
  - `<768px`: same vertical stack; the event rail collapses into a `Sheet` triggered
    from the header; this is a fallback, not a designed-for target (demo is desktop).
- **Optional right event rail:** a 280px collapsible column (`hidden xl:flex`) docked
  right of the video row showing the indexed event stream (live via WebSocket). It is
  chrome, not a fifth region — collapses to a 1px seam with a chevron toggle.

### 2. shadcn/ui components per region

Override the shadcn theme: `--radius: 0.125rem`, dark palette below installed as CSS
vars on `:root` (force `class="dark"` on `<html>`, no theme toggle — forensic tools
don't have a light mode).

| Region | shadcn components | Composition notes |
|---|---|---|
| **Header bar** | `Badge` (run/replay status), `Button` variant=`ghost` size=`sm`, `Separator orientation=vertical`, `Tooltip` | `Badge` for `REPLAY` uses the amber token, outline variant, uppercase mono. `⌘K` is a ghost `Button` with a `kbd`-styled inner span. |
| **Failed-run pane** | `AspectRatio` (16:9) wrapping a raw `<video>` (NOT next/image — it's video), `Skeleton` (loading), `Badge variant=destructive` ("FAILED RUN"), `Tooltip` | Pane label is a top-left absolutely-positioned `Badge`, square, mono, red text on `#1A0F12`. Show `Skeleton` while `clip_url` resolves; swap on `canplay`. |
| **Successful-run pane** | same as above, `Badge` ("SUCCESSFUL RUN") restyled green | Identical structure; the only delta is the green label token. Both `<video>` elements are `preload="metadata"`, `playsInline`, `muted` by default, no native controls (controls live in the shared timeline). |
| **Divergence timeline** | `Slider` (shadcn, single thumb = shared playhead) as the scrub control; custom absolutely-positioned marker `div`; `Tooltip` on the marker; `Button` ghost icons (play/pause, step) using `lucide-react` (`Play`,`Pause`,`SkipBack`); `HoverCard` for marker detail | One `Slider` drives BOTH videos (shared timeline store). The red divergence marker is a non-interactive overlay positioned at `divergence_timestamp / duration`. `HoverCard` on the marker shows the divergence summary + timestamp. Tick labels rendered in mono. |
| **Prompt bar + explanation** | `Input` (canonical question) + `Button` ("Trace divergence"), `Command`/`CommandDialog` (the `Cmd+K` palette), `Skeleton` + streaming text region, `Alert` (error / fallback explanation), `Separator` | The `Input` is square, hairline-bordered, mono placeholder pre-filled with the canonical question. On submit → `Button` enters `loading` (disabled + spinner) → explanation streams into the region below a `Separator`. `Cmd+K` opens `CommandDialog` with preset queries. SSE errors render an `Alert variant=destructive` with the template fallback. |
| **Event rail (optional)** | `ScrollArea`, `Badge` (event template type), `Separator`, `Collapsible` | Each row: mono timestamp + event description, color-coded left 2px border by `run_status`. Reusable event-template chips ("unexpected modal", "stuck spinner", "auth failure") as small square `Badge`s. |

Install set: `npx shadcn@latest add aspect-ratio badge button command dialog input
separator skeleton slider tooltip hover-card alert scroll-area collapsible sheet`.

### 3. Dark forensic color tokens

Slate-based instrument palette (derived from the "Developer Tool / IDE" palette,
darkened toward black-box). Define as both hex and HSL for shadcn vars.

| Token | Hex | HSL | Use |
|---|---|---|---|
| `--background` | `#06090F` | `216 43% 4%` | App shell / void behind everything |
| `--surface` | `#0D131C` | `214 37% 8%` | Video pane letterbox, timeline track, prompt region |
| `--surface-raised` | `#131B27` | `215 33% 12%` | Header bar, event rail, command palette |
| `--border` | `#1E2A3A` | `214 31% 17%` | All 1px hairlines / dividers (the primary separation device) |
| `--border-strong` | `#2C3B4F` | `212 28% 24%` | Focus rings, active slider track |
| `--foreground` | `#E7ECF3` | `214 35% 93%` | Primary text |
| `--muted` | `#8A97A8` | `212 14% 60%` | Secondary labels, axis ticks (passes 4.5:1 on `--surface`) |
| `--muted-dim` | `#5A6678` | `216 15% 41%` | Inactive timeline ticks, disabled |
| `--success` | `#22C55E` | `142 71% 45%` | Successful-run label, success event border |
| `--success-dim` | `#0E2A1A` | `146 50% 11%` | Successful-run label background chip |
| `--danger` | `#F2384A` | `354 88% 58%` | **Divergence marker**, failed-run label, error alert |
| `--danger-bg` | `#1A0F12` | `350 27% 8%` | Failed-run label chip background |
| `--warning` | `#E0A23C` | `38 73% 56%` | `REPLAY` badge only |
| `--ring` | `#2C3B4F` | `212 28% 24%` | Keyboard focus ring (2px, offset 2px) |

**Divergence-marker glow treatment** (the one allowed shadow / the visual climax):

- The marker is a 2px-wide vertical line, full timeline height, color `--danger`.
- A 6px circular cap at the top (`#F2384A`) reads as the "pin" head.
- Resting glow: `box-shadow: 0 0 6px 0 rgba(242,56,74,0.45), 0 0 14px 0 rgba(242,56,74,0.22);`
- On the scrub-arrival "lock" moment, animate a one-shot intensify to
  `0 0 10px 0 rgba(242,56,74,0.7), 0 0 28px 2px rgba(242,56,74,0.35)` over 220ms
  `ease-out`, then settle back to resting (no infinite pulse — a single confident
  flare, like a recorder locking on). `prefers-reduced-motion`: skip the flare, show
  resting glow only.
- The marker sits at `z-30`; videos `z-0`, slider thumb `z-20`, tooltip `z-50`
  (documented z-scale: 0 / 10 / 20 / 30 / 50).

### 4. Typography

- **UI / labels / body:** **IBM Plex Sans** (`--font-sans`). Calm, technical,
  institutional — not a friendly geometric sans.
- **Timestamps / numerics / event descriptions / code-ish data:** **JetBrains Mono**
  (`--font-mono`). All timecodes, durations, `run_id`s, the canonical-question
  placeholder, and timeline tick labels render in mono with `tabular-nums` /
  `font-variant-numeric: tabular-nums` so digits don't jitter while scrubbing.
- Load via `next/font` in `app/layout.tsx`, applied to `<body>` (per Next.js stack
  guideline — never per-page). Tailwind: `fontFamily: { sans: ['var(--font-sans)'],
  mono: ['var(--font-mono)'] }`.
- **Type scale (tight, instrument-grade):**

  | Token | Size / line-height | Weight | Usage |
  |---|---|---|---|
  | `text-data-xl` | 28px / 32px mono | 600 | The locked divergence timestamp (hero number) |
  | `text-h` | 15px / 20px sans | 600 | Region headers ("DIVERGENCE TIMELINE") — uppercase, `tracking-[0.12em]` |
  | `text-body` | 14px / 21px sans | 400 | Explanation prose (line-height 1.5 for readability) |
  | `text-ts` | 13px / 18px mono | 500 | Timestamps, durations, tick labels (tabular-nums) |
  | `text-label` | 11px / 14px sans | 600 | Pane badges, status — uppercase, `tracking-[0.14em]` |
  | `text-meta` | 11px / 14px mono | 400 | Event rail rows, run ids |

  Headers are uppercase + wide tracking + `--muted` color: they read as panel
  engravings, not marketing headings.

### 5. Killshot interaction storyboard

Six visual states. The shared timeline store holds `{ currentTime, duration,
divergenceTime, status }`; one `Slider` and the marker both read it; seeking it seeks
both `<video>` elements.

1. **Idle / loaded.** Both panes show the first frame (poster), paused, dim
   (`opacity-90`). Timeline track is `--surface` with `--muted-dim` ticks; **no red
   marker yet** (divergence unknown until queried). Prompt `Input` is focused on mount,
   placeholder pre-filled mono: `Where did the failed run first diverge from the
   successful one?`. The whole UI is monochrome — deliberately tense, nothing colored.

2. **Query submitted.** User hits Enter (or clicks "Trace divergence", or picks it
   from `Cmd+K`). `Input` locks (readonly, `--muted` text), `Button` → `loading`
   (disabled, 14px spinner). A 2px indeterminate progress hairline animates along the
   top edge of the timeline. Both panes get a faint `Skeleton` shimmer overlay if clip
   URLs are still resolving. Status text under the bar: `tracing divergence…` (mono,
   `--muted`).

3. **Divergence resolved.** `/compare` returns `divergence_timestamp` + both clip
   URLs. The red marker **fades + grows in** at its timeline position over 180ms
   (`scaleY 0.6→1`, `opacity 0→1`, `ease-out`) with the resting glow. The big mono
   timestamp (`text-data-xl`, `--danger`) renders to the right of the prompt bar:
   e.g. `T+00:42.318`. Marker `HoverCard` becomes available.

4. **Synchronized scrub (the hero).** Both videos animate from their current position
   to `divergence_timestamp` *together*. Drive a shared eased tween over ~600ms
   (`ease-out`) updating both `video.currentTime` each frame; the `Slider` thumb glides
   in lockstep; tick label counts up in mono. They must arrive within ±0.5s of each
   other (acceptance criterion) — seek on `canplay`, clamp to `loadedmetadata`
   duration. `prefers-reduced-motion`: hard cut both to the frame, no tween.

5. **Lock-on.** Both panes land on the divergence frame and brighten to `opacity-100`
   with a 1px `--danger` inset ring flashed for 220ms. The marker fires its one-shot
   glow intensify (state from §3) — the visual climax. Brief auto-pause; a
   `Play` affordance appears centered-low on each pane so the user can roll forward
   from the divergence and watch failure vs. success play out.

6. **Explanation streams in.** Below the `Separator` under the prompt bar, Claude's
   plain-English explanation streams token-by-token (SSE) into the `text-body` region:
   a blinking 1ch mono caret at the write head, timestamp citations rendered as inline
   mono chips (`#1A0F12` bg, `--danger` text) that, on hover/click, re-seek both videos
   to that cited time. On SSE failure/timeout, the region swaps to an
   `Alert variant=destructive` containing the template fallback explanation (no dead
   end). When the stream completes, the caret stops and the cited-timestamp chips stay
   interactive — the report is now a navigable forensic document.

**Empty/error states:** no second run for the task → `Alert` "Only one run found for
`{task}` — capture a comparison run." Clip 404 → pane shows a square `--danger` hairline
frame with mono `clip unavailable` and the rest of the flow still runs on the other
pane + explanation. Never crash the grid; never console-error (acceptance criterion).
