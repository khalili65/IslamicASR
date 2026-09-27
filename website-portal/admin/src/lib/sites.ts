export const SITE_IDS = ["website", "website-portal"] as const;

export type SiteId = (typeof SITE_IDS)[number];

export type SiteDef = {
  id: SiteId;
  /** Folder under repo root */
  dir: SiteId;
  label: string;
  webBucket: string;
  mediaBase: string;
};

export const SITES: Record<SiteId, SiteDef> = {
  website: {
    id: "website",
    dir: "website",
    label: "درس‌گفتارهای استاد بیات",
    webBucket: "islamic-asr-web",
    mediaBase: "https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir",
  },
  "website-portal": {
    id: "website-portal",
    dir: "website-portal",
    label: "پورتال درس‌گفتارها",
    webBucket: "islamic-asr-portal-web",
    mediaBase:
      "https://islamic-asr-portal-media.s3.ir-thr-at1.arvanstorage.ir",
  },
};

export function isSiteId(v: unknown): v is SiteId {
  return typeof v === "string" && (SITE_IDS as readonly string[]).includes(v);
}

export function parseSiteId(v: unknown, fallback: SiteId = "website"): SiteId {
  return isSiteId(v) ? v : fallback;
}

/** Append ?site= / &site= for admin API calls. */
export function withSite(path: string, site: SiteId): string {
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}site=${encodeURIComponent(site)}`;
}

export function siteFromRequest(req: Request, fallback: SiteId = "website"): SiteId {
  const url = new URL(req.url);
  const q = url.searchParams.get("site");
  if (isSiteId(q)) return q;
  const h = req.headers.get("x-admin-site");
  if (isSiteId(h)) return h;
  return fallback;
}

/** Serve site public images through the admin origin (client-safe). */
export function mediaUrl(siteId: SiteId, avatar: string): string {
  if (!avatar) return "";
  if (avatar.startsWith("http://") || avatar.startsWith("https://")) return avatar;
  const clean = avatar.startsWith("/") ? avatar.slice(1) : avatar;
  return `/api/media/${clean}?site=${encodeURIComponent(siteId)}`;
}
