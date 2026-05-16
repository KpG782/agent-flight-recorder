/**
 * Placeholder shell — scaffold only. The killshot split-pane forensic page
 * (/runs/[task]/compare) is built later by the UI agent per
 * specs/phase-3-ui.md. This page only proves the dark forensic theme tokens
 * and font wiring render; no feature UI.
 */
export default function Home() {
  return (
    <main className="grid h-dvh grid-rows-[40px_1fr] overflow-hidden">
      <header className="flex items-center gap-3 border-b border-border bg-surface-raised px-4">
        <span className="text-label uppercase tracking-[0.14em] text-foreground">
          Agent Flight Recorder
        </span>
        <span className="h-3 w-px bg-border" />
        <span className="font-mono text-meta text-muted">
          task: demo_login_flow
        </span>
        <span className="ml-auto rounded border border-warning px-2 py-0.5 font-mono text-meta uppercase tracking-[0.14em] text-warning">
          scaffold
        </span>
      </header>

      <section className="flex flex-col items-center justify-center gap-4 bg-background px-6 text-center">
        <h1 className="text-h uppercase tracking-[0.12em] text-muted">
          Forensic split-pane UI lands here
        </h1>
        <p className="max-w-md text-body text-muted">
          Two-run differential divergence replay. This is the scaffold
          placeholder; the killshot page is built in Phase 3.
        </p>
        <code className="border border-border bg-surface px-3 py-2 font-mono text-ts text-foreground">
          T+00:00.000 · awaiting capture → index → search
        </code>
        <div className="flex gap-3 font-mono text-meta">
          <span className="text-success">success</span>
          <span className="text-muted-dim">·</span>
          <span className="text-danger">divergence</span>
        </div>
      </section>
    </main>
  );
}
