"use client";

/**
 * Hand-rolled forensic UI primitives (specs/phase-3-ui.md §0–§3). Square
 * (radius ≤2px), hairline borders not shadows, monochrome slate + green/red.
 * Built without the shadcn CLI on purpose: zero extra npm deps keeps the demo
 * robust and offline-installable; the styling contract (the brief) is what
 * matters, not the generator.
 */
import * as React from "react";

export function cx(...c: Array<string | false | null | undefined>): string {
  return c.filter(Boolean).join(" ");
}

/* SVG icons (24x24 viewBox, currentColor) — never emojis as UI icons. */
function Svg(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    />
  );
}
export const PlayIcon = (p: React.SVGProps<SVGSVGElement>) => (
  <Svg {...p}>
    <polygon points="6 4 20 12 6 20 6 4" fill="currentColor" stroke="none" />
  </Svg>
);
export const PauseIcon = (p: React.SVGProps<SVGSVGElement>) => (
  <Svg {...p}>
    <rect x="6" y="5" width="4" height="14" fill="currentColor" stroke="none" />
    <rect x="14" y="5" width="4" height="14" fill="currentColor" stroke="none" />
  </Svg>
);
export const TargetIcon = (p: React.SVGProps<SVGSVGElement>) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8" />
    <line x1="12" y1="2" x2="12" y2="6" />
    <line x1="12" y1="18" x2="12" y2="22" />
    <line x1="2" y1="12" x2="6" y2="12" />
    <line x1="18" y1="12" x2="22" y2="12" />
  </Svg>
);

export function Button({
  className,
  variant = "ghost",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "ghost" | "solid" | "danger";
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-none border px-3 h-8 text-label uppercase tracking-[0.12em] transition-colors duration-150 ease-out disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";
  const v = {
    ghost:
      "border-border bg-transparent text-muted hover:text-foreground hover:border-border-strong",
    solid:
      "border-border-strong bg-surface-raised text-foreground hover:bg-surface",
    danger: "border-danger bg-danger-bg text-danger hover:brightness-125",
  }[variant];
  return <button className={cx(base, v, className)} {...props} />;
}

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(function Input({ className, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={cx(
        "h-9 w-full rounded-none border border-border bg-surface px-3 font-mono text-ts text-foreground placeholder:text-muted-dim focus-visible:outline-none focus-visible:border-border-strong focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  );
});

export function Badge({
  children,
  tone = "muted",
  className,
}: {
  children: React.ReactNode;
  tone?: "muted" | "success" | "danger" | "warning";
  className?: string;
}) {
  const t = {
    muted: "border-border text-muted bg-surface",
    success: "border-success/50 text-success bg-success-dim",
    danger: "border-danger/50 text-danger bg-danger-bg",
    warning: "border-warning text-warning bg-transparent",
  }[tone];
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-none border px-2 py-0.5 text-label uppercase tracking-[0.14em]",
        t,
        className,
      )}
    >
      {children}
    </span>
  );
}

/** A video pane: AspectRatio-ish 16:9 box, square label badge, skeleton until
 * canplay, graceful "clip unavailable" on error (never crash the grid). */
export function VideoPane({
  label,
  tone,
  src,
  videoRef,
  onReady,
  dim = false,
  flash = false,
}: {
  label: string;
  tone: "success" | "danger";
  src: string | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onReady?: () => void;
  dim?: boolean;
  flash?: boolean;
}) {
  const [state, setState] = React.useState<"loading" | "ready" | "error">(
    "loading",
  );
  React.useEffect(() => {
    if (src) setState("loading");
  }, [src]);
  return (
    <div className="relative h-full w-full overflow-hidden bg-surface">
      <span
        className={cx(
          "absolute left-3 top-3 z-10 inline-flex items-center rounded-none border px-2 py-0.5 text-label uppercase tracking-[0.14em]",
          tone === "danger"
            ? "border-danger/60 bg-danger-bg text-danger"
            : "border-success/60 bg-success-dim text-success",
        )}
      >
        {label}
      </span>
      {/* scanline instrument texture — auto-disabled for reduced motion */}
      <div className="afr-scanline pointer-events-none absolute inset-0 z-[8]" />
      {/* lock-on inset ring flash (storyboard §5) */}
      {flash && (
        <div
          className="pointer-events-none absolute inset-0 z-[9] animate-[afrflash_220ms_ease-out]"
          style={{ boxShadow: "inset 0 0 0 1px var(--danger)" }}
        />
      )}
      {state === "loading" && src && (
        <div className="absolute inset-0 z-[5] animate-pulse bg-surface-raised/60" />
      )}
      {state === "error" && (
        <div className="absolute inset-0 z-[5] flex items-center justify-center border border-danger/40">
          <span className="font-mono text-ts text-danger">clip unavailable</span>
        </div>
      )}
      {src ? (
        <video
          ref={videoRef}
          src={src}
          preload="metadata"
          playsInline
          muted
          aria-label={`${label} video`}
          className={cx(
            "h-full w-full object-contain transition-opacity duration-200 ease-out",
            dim ? "opacity-90" : "opacity-100",
          )}
          onCanPlay={() => {
            setState("ready");
            onReady?.();
          }}
          onError={() => setState("error")}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <span className="font-mono text-meta text-muted-dim">
            awaiting clip
          </span>
        </div>
      )}
    </div>
  );
}
