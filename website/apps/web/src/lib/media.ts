/**
 * Local JSON stores paths like `/audio/bayat/marefat_nafs/001/001_play.m4a`.
 * In production, Cloudflare Pages sets NEXT_PUBLIC_MEDIA_BASE to the R2 public
 * host (e.g. https://pub-….r2.dev) so the same JSON works without rebuilding
 * URLs for every environment.
 */
export function resolveMediaUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;

  const base = (process.env.NEXT_PUBLIC_MEDIA_BASE || "").replace(/\/$/, "");
  if (!base) return url;

  if (url.startsWith("/audio/")) {
    return `${base}/${url.slice("/audio/".length)}`;
  }
  if (url.startsWith("/")) {
    return `${base}${url}`;
  }
  return `${base}/${url}`;
}
