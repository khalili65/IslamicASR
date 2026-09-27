import { SITES, type SiteKey } from "@/constants/theme";
import type {
  CourseIndex,
  CuesFile,
  Lecturer,
  SessionPayload,
  SiteIndex,
} from "./types";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`Failed ${res.status}: ${url}`);
  return res.json() as Promise<T>;
}

function mapLecturers(index: SiteIndex, site: SiteKey): Lecturer[] {
  const cfg = SITES[site];
  return (index.lecturers || []).map((l) => ({
    ...l,
    // Match Shojaee’s specialty line for Bayat in the mobile library.
    title: l.slug === "bayat" ? "استاد اخلاق و عرفان" : l.title,
    site,
    dataBase: cfg.dataBase,
    mediaBase: cfg.mediaBase,
  }));
}

/** Preferred library order: Shojaee first, Bayat last. */
function lecturerSortKey(slug: string): number {
  if (slug === "shojai") return 0;
  if (slug === "bayat") return 1000;
  return 100;
}

/** Unified library: Bayat site + portal lecturers in one list. */
export async function loadLibrary(): Promise<Lecturer[]> {
  const [bayat, portal] = await Promise.all([
    fetchJson<SiteIndex>(`${SITES.website.dataBase}/data/index.json`),
    fetchJson<SiteIndex>(`${SITES.portal.dataBase}/data/index.json`),
  ]);
  const all = [
    ...mapLecturers(portal, "portal"),
    ...mapLecturers(bayat, "website"),
  ];
  return all.sort(
    (a, b) =>
      lecturerSortKey(a.slug) - lecturerSortKey(b.slug) ||
      a.name.localeCompare(b.name, "fa"),
  );
}

export async function loadCourse(
  lecturer: Lecturer,
  courseSlug: string,
): Promise<CourseIndex> {
  return fetchJson<CourseIndex>(
    `${lecturer.dataBase}/data/${lecturer.slug}/${courseSlug}/course.json`,
  );
}

export async function loadSession(
  lecturer: Lecturer,
  courseSlug: string,
  sessionId: string,
): Promise<SessionPayload> {
  return fetchJson<SessionPayload>(
    `${lecturer.dataBase}/data/${lecturer.slug}/${courseSlug}/${sessionId}.json`,
  );
}

export async function loadCues(
  lecturer: Lecturer,
  courseSlug: string,
  sessionId: string,
): Promise<CuesFile> {
  return fetchJson<CuesFile>(
    `${lecturer.dataBase}/data/${lecturer.slug}/${courseSlug}/${sessionId}.cues.json`,
  );
}
