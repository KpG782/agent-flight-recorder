/**
 * Typed API client for apps/api. Shapes come from @afr/types (the frozen
 * api-contracts.md mirror). No data-fetching library — a single page with two
 * calls (compare + SSE explain) does not warrant TanStack Query; native
 * fetch/EventSource keeps the demo dependency-free and robust.
 */
import type { CompareResponse } from "@afr/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

/** The one canonical forensic question (prefilled in the prompt bar). */
export const CANONICAL_QUERY =
  "Where did the failed run first diverge from the successful one?";

/** Logical run length (max event offset in the demo); the timeline is 0..this.
 * Each video maps the same fraction → its own duration, so both panes land on
 * the divergence frame in lockstep regardless of clip length. */
export const RUN_DURATION_S = 30;

export async function compare(task: string): Promise<CompareResponse> {
  const res = await fetch(
    `${API_BASE}/tasks/${encodeURIComponent(task)}/compare`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    },
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `compare failed (${res.status})`);
  }
  return res.json();
}

export function explainUrl(task: string, query: string): string {
  return `${API_BASE}/tasks/${encodeURIComponent(
    task,
  )}/explain?query=${encodeURIComponent(query)}`;
}
