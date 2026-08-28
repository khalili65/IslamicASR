export function toPersianDigits(value: string | number): string {
  return String(value).replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[Number(d)]);
}

export function formatClock(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const body =
    h > 0
      ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
      : `${m}:${String(s).padStart(2, "0")}`;
  return toPersianDigits(body);
}

/** How far ahead of the playhead we pick the active cue (seconds).
 *  Kept at 0 now that we poll currentTime every animation frame; a lead
 *  made the text feel early once the underlying clocks already agree.
 */
export const CUE_LEAD_SECONDS = 0;

export function findCueIndex(
  cues: { start: number; end: number }[],
  t: number,
): number {
  if (!cues.length) return -1;
  // Look ahead so the line lands with the speech. ASR word timestamps and
  // the browser's sparse timeupdate events otherwise make text feel late.
  const at = t + CUE_LEAD_SECONDS;
  let lo = 0;
  let hi = cues.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const cue = cues[mid];
    if (at < cue.start) hi = mid - 1;
    else if (at >= cue.end) lo = mid + 1;
    else return mid;
  }
  // Do not keep a finished cue on screen after its end — blank is better
  // than showing yesterday's sentence while new speech has started.
  return -1;
}
