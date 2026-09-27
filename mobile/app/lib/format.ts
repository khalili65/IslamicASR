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

export const CUE_LEAD_SECONDS = 0;

export function findCueIndex(
  cues: { start: number; end: number }[],
  t: number,
): number {
  if (!cues.length) return -1;
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
  return -1;
}

export function resolveMediaUrl(
  url: string | null | undefined,
  mediaBase: string,
): string {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  const base = mediaBase.replace(/\/$/, "");
  if (url.startsWith("/audio/")) {
    return `${base}/${url.slice("/audio/".length)}`;
  }
  if (url.startsWith("/")) return `${base}${url}`;
  return `${base}/${url}`;
}

export function resolveAssetUrl(
  path: string | null | undefined,
  dataBase: string,
): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const base = dataBase.replace(/\/$/, "");
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${base}${clean.split("?")[0]}`;
}
