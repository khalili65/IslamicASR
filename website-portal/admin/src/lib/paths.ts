import path from "path";
import { SITES, type SiteId, parseSiteId } from "./sites";

/** Monorepo root (IslamASR). Override with REPO_ROOT in production. */
export function repoRoot(): string {
  if (process.env.REPO_ROOT) {
    return path.resolve(process.env.REPO_ROOT);
  }
  // admin/ → website-portal/ → repo
  return path.resolve(process.cwd(), "../..");
}

export function siteRoot(siteId: SiteId): string {
  return path.join(repoRoot(), SITES[siteId].dir);
}

export function siteLabel(siteId: SiteId): string {
  return SITES[siteId].label;
}

export function siteArvanDefaults(siteId: SiteId): {
  webBucket: string;
  mediaBase: string;
} {
  const s = SITES[siteId];
  return { webBucket: s.webBucket, mediaBase: s.mediaBase };
}

/** @deprecated prefer explicit siteId — kept for env-only scripts */
export function defaultSiteId(): SiteId {
  if (process.env.SITE_ROOT) {
    const base = path.basename(path.resolve(process.env.SITE_ROOT));
    return parseSiteId(base, "website");
  }
  return "website";
}

export function pathsFor(siteId: SiteId) {
  const root = siteRoot(siteId);
  return {
    siteRoot: root,
    content: () => path.join(root, "content"),
    data: () => path.join(root, "apps/web/public/data"),
    images: () => path.join(root, "apps/web/public/images"),
    lecturerImages: () => path.join(root, "apps/web/public/images/lecturers"),
    siteWeb: () => path.join(root, "apps/web"),
    deployScript: () => path.join(root, "scripts/deploy_arvan_web.py"),
  };
}

export const paths = {
  audios: () => path.join(repoRoot(), "Audios"),
  buildScript: () => path.join(repoRoot(), "website/tools/build_content.py"),
  python: () =>
    process.env.PYTHON_BIN || path.join(repoRoot(), ".venv/bin/python"),
};
