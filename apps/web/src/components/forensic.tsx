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
}: {
  label: string;
  tone: "success" | "danger";
  src: string | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onReady?: () => void;
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
          className="h-full w-full object-contain"
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
