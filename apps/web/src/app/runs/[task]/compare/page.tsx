"use client";

/**
 * The killshot — split-pane forensic divergence replay (specs/phase-3-ui.md).
 *
 * State machine (storyboard §5): idle → tracing → resolved → scrubbing →
 * locked. One shared timeline (0..RUN_DURATION_S); the Slider + the red marker
 * read it; seeking it seeks BOTH <video> elements by the SAME fraction so they
 * arrive on the divergence frame in lockstep (acceptance: within ±0.5s).
 */
import * as React from "react";
import { useParams } from "next/navigation";
import type { CompareResponse, WsEventFrame } from "@afr/types";
import {
  API_BASE,
  CANONICAL_QUERY,
  RUN_DURATION_S,
  WS_BASE,
  compare,
  explainUrl,
} from "@/lib/api";
import { fmtTimecode } from "@/lib/format";
import {
  Badge,
  Button,
  Input,
  PauseIcon,
  PlayIcon,
  TargetIcon,
  VideoPane,
  cx,
} from "@/components/forensic";

type Status = "idle" | "tracing" | "resolved" | "scrubbing" | "locked";

const PRESET_QUERIES = [
  CANONICAL_QUERY,
  "Show the authentication failure",
  "What did the user type into the password field",
];

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

export default function ComparePage() {
  const params = useParams<{ task: string }>();
  const task = params.task ?? "demo_login_flow";

  const [status, setStatus] = React.useState<Status>("idle");
  const [query, setQuery] = React.useState(CANONICAL_QUERY);
  const [result, setResult] = React.useState<CompareResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [explanation, setExplanation] = React.useState("");
  const [streaming, setStreaming] = React.useState(false);
  const [fallback, setFallback] = React.useState(false);
  const [fraction, setFraction] = React.useState(0); // 0..1 of RUN_DURATION_S
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const [railOpen, setRailOpen] = React.useState(true);
  const [events, setEvents] = React.useState<WsEventFrame[]>([]);
  const [markerFlare, setMarkerFlare] = React.useState(false);
  const [playing, setPlaying] = React.useState(false);

  const failRef = React.useRef<HTMLVideoElement | null>(null);
  const successRef = React.useRef<HTMLVideoElement | null>(null);
  const esRef = React.useRef<EventSource | null>(null);
  const promptRef = React.useRef<HTMLInputElement | null>(null);
  const rafRef = React.useRef<number | null>(null);
  const paletteRef = React.useRef<HTMLButtonElement | null>(null);
  const dim = status === "idle" || status === "tracing";

  const divergenceFraction = result
    ? Math.min(1, result.divergence_timestamp / RUN_DURATION_S)
    : null;
  const currentSeconds = fraction * RUN_DURATION_S;

  // Prompt focused on mount (storyboard §1).
  React.useEffect(() => {
    promptRef.current?.focus();
  }, []);

  // Cmd+K command palette.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      } else if (e.key === "Escape") {
        setPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Move focus into the palette when it opens (keyboard a11y), restore to the
  // prompt when it closes.
  React.useEffect(() => {
    if (paletteOpen) {
      const t = window.setTimeout(() => paletteRef.current?.focus(), 0);
      return () => window.clearTimeout(t);
    }
    promptRef.current?.focus();
  }, [paletteOpen]);

  // WS event rail (best-effort; truth is the webhook path). Never throw.
  React.useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS_BASE}?run_id=demo`);
      ws.onmessage = (ev) => {
        try {
          const frame = JSON.parse(ev.data) as WsEventFrame;
          if (frame?.type === "event")
            setEvents((prev) => [...prev.slice(-49), frame]);
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onerror = () => ws?.close();
    } catch {
      /* WS unavailable — rail just stays empty */
    }
    return () => ws?.close();
  }, []);

  function seekBoth(f: number) {
    const clamped = Math.max(0, Math.min(1, f));
    for (const ref of [failRef, successRef]) {
      const v = ref.current;
      if (v && Number.isFinite(v.duration) && v.duration > 0) {
        v.currentTime = clamped * v.duration;
      }
    }
  }

  function tweenToDivergence(targetFraction: number) {
    if (prefersReducedMotion()) {
      setFraction(targetFraction);
      seekBoth(targetFraction);
      lockOn();
      return;
    }
    setStatus("scrubbing");
    const start = fraction;
    const t0 = performance.now();
    const dur = 600;
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3); // ease-out cubic
      const f = start + (targetFraction - start) * eased;
      setFraction(f);
      seekBoth(f);
      if (p < 1) requestAnimationFrame(step);
      else lockOn();
    };
    requestAnimationFrame(step);
  }

  function lockOn() {
    setStatus("locked");
    setPlaying(false);
    setMarkerFlare(true);
    window.setTimeout(() => setMarkerFlare(false), 240);
  }

  // Synced playback: both <video>s play from the current position; a rAF loop
  // advances the shared timeline from the (primary) failed video's clock so
  // the slider + marker track it. Roll forward from the divergence to watch
  // failure vs. success play out (storyboard §5).
  function pauseBoth() {
    failRef.current?.pause();
    successRef.current?.pause();
    setPlaying(false);
  }

  function togglePlay() {
    if (!result) return;
    if (playing) {
      pauseBoth();
      return;
    }
    const f = failRef.current;
    const s = successRef.current;
    if (!f || !s) return;
    void f.play().catch(() => {});
    void s.play().catch(() => {});
    setPlaying(true);
  }

  React.useEffect(() => {
    if (!playing) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }
    const tick = () => {
      const f = failRef.current;
      if (f && Number.isFinite(f.duration) && f.duration > 0) {
        const frac = Math.min(1, f.currentTime / f.duration);
        setFraction(frac);
        if (f.ended || frac >= 0.999) {
          pauseBoth();
          return;
        }
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  function jumpToDivergence() {
    if (divergenceFraction === null) return;
    pauseBoth();
    if (prefersReducedMotion()) {
      setFraction(divergenceFraction);
      seekBoth(divergenceFraction);
      lockOn();
    } else {
      tweenToDivergence(divergenceFraction);
    }
  }

  function startExplanation(q: string) {
    esRef.current?.close();
    setExplanation("");
    setFallback(false);
    setStreaming(true);
    const es = new EventSource(explainUrl(task, q));
    esRef.current = es;
    es.addEventListener("token", (e) => {
      try {
        const d = JSON.parse((e as MessageEvent).data);
        setExplanation((prev) => prev + (d.text ?? ""));
      } catch {
        /* ignore */
      }
    });
    es.addEventListener("error", (e) => {
      try {
        const d = JSON.parse((e as MessageEvent).data);
        if (d?.message) setFallback(true);
      } catch {
        /* network error event has no data — keep stream open for fallback token */
      }
    });
    es.addEventListener("done", () => {
      setStreaming(false);
      es.close();
    });
    es.onerror = () => {
      // Transport died with no server 'done' — stop spinner, keep partial text.
      setStreaming(false);
      es.close();
    };
  }

  async function runTrace(q: string) {
    setError(null);
    setStatus("tracing");
    setExplanation("");
    try {
      const res = await compare(task);
      setResult(res);
      setStatus("resolved");
      const target = Math.min(1, res.divergence_timestamp / RUN_DURATION_S);
      // Wait a tick so clip srcs are bound + metadata can load before seeking.
      window.setTimeout(() => tweenToDivergence(target), 120);
      startExplanation(q);
    } catch (err) {
      setError(err instanceof Error ? err.message : "trace failed");
      setStatus("idle");
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (status === "tracing") return;
    runTrace(query);
  }

  function reseekTo(seconds: number) {
    const f = Math.min(1, seconds / RUN_DURATION_S);
    setFraction(f);
    seekBoth(f);
  }

  // Inline timestamp chips (T+SS.SS) in the explanation become re-seek links.
  const explanationNodes = React.useMemo(() => {
    // We render plain text, not markdown — strip Claude's occasional **bold**
    // and ## headings so they don't show as literal glyphs.
    const clean = explanation.replace(/\*\*/g, "").replace(/^#{1,6}\s*/gm, "");
    const parts = clean.split(/(T\+\d{1,3}(?:\.\d+)?s)/g);
    return parts.map((p, i) => {
      const m = p.match(/^T\+(\d{1,3}(?:\.\d+)?)s$/);
      if (!m) return <React.Fragment key={i}>{p}</React.Fragment>;
      const secs = parseFloat(m[1]);
      return (
        <button
          key={i}
          onClick={() => reseekTo(secs)}
          className="mx-0.5 inline-block rounded-none border border-danger/40 bg-danger-bg px-1 font-mono text-[12px] text-danger hover:brightness-125"
        >
          {p}
        </button>
      );
    });
  }, [explanation]);

  const clipFail = result?.failed_clip_url ?? null;
  const clipSuccess = result?.success_clip_url ?? null;

  return (
    <main className="grid h-dvh grid-rows-[40px_minmax(0,1fr)_96px_auto] overflow-hidden bg-background">
      {/* ── Header ── */}
      <header className="flex items-center gap-3 border-b border-border bg-surface-raised px-4">
        <span className="text-label uppercase tracking-[0.14em] text-foreground">
          Agent Flight Recorder
        </span>
        <span className="h-3 w-px bg-border" />
        <span className="font-mono text-meta text-muted">task: {task}</span>
        <span className="h-3 w-px bg-border" />
        <Badge tone="warning">replay</Badge>
        <div className="ml-auto flex items-center gap-3">
          <button
            onClick={() => setRailOpen((o) => !o)}
            aria-pressed={railOpen}
            className="cursor-pointer rounded-none font-mono text-meta text-muted transition-colors duration-150 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {railOpen ? "hide rail" : "show rail"}
          </button>
          <Button
            variant="ghost"
            onClick={() => setPaletteOpen(true)}
            aria-label="Open command palette"
            aria-keyshortcuts="Meta+K Control+K"
            className="cursor-pointer"
          >
            <span className="rounded-none border border-border px-1 font-mono text-[10px]">
              ⌘K
            </span>
          </Button>
        </div>
      </header>

      {/* ── Video row + optional event rail ── */}
      <section className="grid min-h-0 grid-cols-1 divide-x divide-border md:grid-cols-2 xl:grid-cols-[1fr_1fr_280px]">
        <VideoPane
          label="Failed run"
          tone="danger"
          src={clipFail}
          videoRef={failRef}
          dim={dim}
          flash={markerFlare}
        />
        <VideoPane
          label="Successful run"
          tone="success"
          src={clipSuccess}
          videoRef={successRef}
          dim={dim}
          flash={markerFlare}
        />
        <aside
          className={cx(
            "hidden min-h-0 flex-col overflow-hidden bg-surface-raised xl:flex",
            railOpen ? "" : "xl:hidden",
          )}
        >
          <div className="border-b border-border px-3 py-2 text-label uppercase tracking-[0.12em] text-muted">
            Event stream
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {events.length === 0 && (
              <p className="px-3 py-3 font-mono text-meta text-muted-dim">
                awaiting live events…
              </p>
            )}
            {events.map((ev, i) => (
              <div
                key={i}
                className={cx(
                  "border-b border-border/60 px-3 py-2",
                  ev.template_tag ? "border-l-2 border-l-danger" : "border-l-2 border-l-border",
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-meta text-muted">
                    {fmtTimecode(ev.t_offset_s)}
                  </span>
                  {ev.template_tag && (
                    <Badge tone="danger">{ev.template_tag.replace("_", " ")}</Badge>
                  )}
                </div>
                <p className="mt-1 font-mono text-meta text-foreground/80">
                  {ev.description}
                </p>
              </div>
            ))}
          </div>
        </aside>
      </section>

      {/* ── Divergence timeline ── */}
      <section className="relative flex flex-col justify-center border-b border-t border-border bg-surface px-4">
        <div className="flex items-center justify-between pb-2">
          <div className="flex items-center gap-3">
            <span className="text-label uppercase tracking-[0.12em] text-muted">
              Divergence timeline
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={togglePlay}
                disabled={!result}
                aria-label={playing ? "Pause both runs" : "Play both runs"}
                className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-none border border-border text-muted transition-colors duration-150 hover:border-border-strong hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {playing ? <PauseIcon /> : <PlayIcon />}
              </button>
              <button
                onClick={jumpToDivergence}
                disabled={divergenceFraction === null}
                aria-label="Jump to divergence"
                title="Jump to divergence"
                className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-none border border-border text-danger transition-colors duration-150 hover:border-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <TargetIcon />
              </button>
            </div>
          </div>
          <span className="font-mono text-ts text-muted" aria-live="off">
            {fmtTimecode(currentSeconds)} / {fmtTimecode(RUN_DURATION_S)}
          </span>
        </div>
        <div className="relative h-6">
          {/* track */}
          <div className="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 bg-border" />
          {/* divergence marker (the visual climax) */}
          {divergenceFraction !== null && (
            <div
              key={result?.divergence_timestamp}
              className="afr-marker-in absolute top-0 z-30 h-full w-[2px] -translate-x-1/2 bg-danger"
              style={{
                left: `${divergenceFraction * 100}%`,
                boxShadow: markerFlare
                  ? "0 0 10px 0 rgba(242,56,74,0.7), 0 0 28px 2px rgba(242,56,74,0.35)"
                  : "0 0 6px 0 rgba(242,56,74,0.45), 0 0 14px 0 rgba(242,56,74,0.22)",
                transition: "box-shadow 220ms ease-out",
              }}
              title={`divergence ${fmtTimecode(
                result?.divergence_timestamp ?? 0,
              )}`}
            >
              <span className="absolute -top-1 left-1/2 h-[6px] w-[6px] -translate-x-1/2 rounded-full bg-danger" />
            </div>
          )}
          {/* scrub slider (single shared playhead) */}
          <input
            type="range"
            min={0}
            max={1000}
            value={Math.round(fraction * 1000)}
            onChange={(e) => {
              const f = Number(e.target.value) / 1000;
              if (playing) pauseBoth();
              setStatus("scrubbing");
              setFraction(f);
              seekBoth(f);
            }}
            aria-label="Timeline scrub — seeks both runs"
            aria-valuetext={fmtTimecode(currentSeconds)}
            className="absolute inset-0 z-20 w-full cursor-pointer appearance-none bg-transparent [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-[3px] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:bg-foreground"
          />
        </div>
      </section>

      {/* ── Prompt bar + streamed explanation ── */}
      <section className="max-h-[240px] overflow-hidden bg-surface-raised px-4 py-3">
        <form onSubmit={onSubmit} className="flex items-center gap-3">
          <Input
            ref={promptRef}
            value={query}
            readOnly={status === "tracing"}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={CANONICAL_QUERY}
            aria-label="forensic query"
          />
          <Button
            type="submit"
            variant="solid"
            disabled={status === "tracing"}
            className="shrink-0"
          >
            {status === "tracing" ? "tracing…" : "Trace divergence"}
          </Button>
          {result && (
            <span className="shrink-0 font-mono text-data-xl text-danger">
              {fmtTimecode(result.divergence_timestamp)}
            </span>
          )}
        </form>

        <div className="mt-2 h-px bg-border" />

        <div
          className="mt-2 max-h-[150px] overflow-y-auto"
          aria-live="polite"
          role="status"
        >
          {error && (
            <div
              role="alert"
              className="rounded-none border border-danger bg-danger-bg px-3 py-2 font-mono text-ts text-danger"
            >
              {error}
              <span className="ml-2 text-muted-dim">· api {API_BASE}</span>
            </div>
          )}
          {!error && status === "idle" && (
            <p className="font-mono text-meta text-muted-dim">
              ask the canonical question to trace the divergence
            </p>
          )}
          {!error && status === "tracing" && (
            <p className="font-mono text-meta text-muted">
              tracing divergence…
            </p>
          )}
          {!error && status !== "idle" && status !== "tracing" && (
            <div className="text-body leading-relaxed text-foreground">
              {fallback && (
                <span className="mb-1 mr-2 inline-block rounded-none border border-danger/50 bg-danger-bg px-1 font-mono text-[11px] uppercase text-danger">
                  template fallback
                </span>
              )}
              {explanationNodes}
              {streaming && (
                <span className="ml-0.5 inline-block w-[1ch] animate-pulse font-mono text-danger">
                  ▍
                </span>
              )}
            </div>
          )}
        </div>
      </section>

      {/* ── Cmd+K palette ── */}
      {paletteOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-background/70 pt-[18vh]"
          onClick={() => setPaletteOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Preset forensic queries"
            className="w-[560px] max-w-[90vw] rounded-[2px] border border-border-strong bg-surface-raised"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border px-3 py-2 font-mono text-meta text-muted">
              <span>preset forensic queries</span>
              <span className="text-muted-dim">esc to close</span>
            </div>
            {PRESET_QUERIES.map((q, i) => (
              <button
                key={q}
                ref={i === 0 ? paletteRef : undefined}
                onClick={() => {
                  setPaletteOpen(false);
                  setQuery(q);
                  runTrace(q);
                }}
                className="block w-full cursor-pointer border-b border-border/60 px-3 py-2 text-left font-mono text-ts text-foreground transition-colors duration-150 hover:bg-surface focus-visible:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
