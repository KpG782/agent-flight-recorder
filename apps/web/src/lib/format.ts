/** T+MM:SS.mmm — the forensic timecode format (mono, tabular-nums). */
export function fmtTimecode(seconds: number): string {
  const s = Math.max(0, seconds);
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  const ms = Math.floor((s - Math.floor(s)) * 1000);
  return `T+${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}.${String(
    ms,
  ).padStart(3, "0")}`;
}
