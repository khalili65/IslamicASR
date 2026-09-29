import { SITES, type SiteKey } from "@/constants/theme";
import {
  normalizedIncludes,
  tokenizePersian,
  tokensMatch,
} from "@/lib/persian";

export type SearchCatalogCourse = {
  slug: string;
  title: string;
  format?: string;
};

export type SearchCatalogLecturer = {
  slug: string;
  name: string;
  format?: string;
  source?: string;
  site: SiteKey;
  dataBase: string;
  courses: SearchCatalogCourse[];
};

export type SearchCatalog = {
  v: number;
  lecturers: SearchCatalogLecturer[];
};

type Chunk = {
  i: number;
  t: string;
  start?: number | null;
};

type SearchDoc = {
  c: string;
  ct: string;
  s: string;
  t: string;
  k: string;
  kind: "cue" | "text";
  p: Chunk[];
};

export type LecturerSearchIndex = {
  v: number;
  l: string;
  ln: string;
  format?: string;
  source?: string;
  docs: SearchDoc[];
};

export type SearchHit = {
  lecturer: string;
  lecturerName: string;
  course: string;
  courseTitle: string;
  sessionId: string;
  sessionTitle: string;
  kind: "cue" | "text";
  text: string;
  paraIndex: number;
  start: number | null;
  site: SiteKey;
};

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`Failed ${res.status}: ${url}`);
  return res.json() as Promise<T>;
}

type RawCatalog = {
  v: number;
  lecturers: Array<{
    slug: string;
    name: string;
    format?: string;
    source?: string;
    courses: SearchCatalogCourse[];
  }>;
};

/** Merge website + portal search catalogs (same indexes the sites ship). */
export async function loadSearchCatalog(): Promise<SearchCatalog> {
  const entries = await Promise.all(
    (Object.keys(SITES) as SiteKey[]).map(async (site) => {
      const cfg = SITES[site];
      try {
        const raw = await fetchJson<RawCatalog>(
          `${cfg.dataBase}/data/search/catalog.json`,
        );
        return (raw.lecturers || []).map((l) => ({
          ...l,
          site,
          dataBase: cfg.dataBase,
        }));
      } catch {
        return [] as SearchCatalogLecturer[];
      }
    }),
  );
  return { v: 1, lecturers: entries.flat() };
}

export async function loadLecturerSearchIndex(
  lecturer: SearchCatalogLecturer,
): Promise<LecturerSearchIndex> {
  return fetchJson<LecturerSearchIndex>(
    `${lecturer.dataBase}/data/search/${lecturer.slug}.json`,
  );
}

function chunkMatches(text: string, query: string, tokens: string[]): boolean {
  if (!text) return false;
  if (text.includes(query)) return true;
  if (normalizedIncludes(text, query)) return true;
  if (tokens.length > 0 && tokensMatch(text, tokens)) return true;
  return false;
}

export function runTokenSearch(opts: {
  query: string;
  lecturers: SearchCatalogLecturer[];
  indexes: Record<string, LecturerSearchIndex>;
  lecturerFilter: string; // "all" | slug
  courseFilter: string; // "all" | slug
}): SearchHit[] {
  const q = opts.query.trim();
  if (q.length < 2) return [];

  const tokens = tokenizePersian(q);
  const results: SearchHit[] = [];
  const needed =
    opts.lecturerFilter === "all"
      ? opts.lecturers
      : opts.lecturers.filter((l) => l.slug === opts.lecturerFilter);

  for (const meta of needed) {
    const bundle = opts.indexes[meta.slug];
    if (!bundle) continue;
    const lecturerName = meta.name || bundle.ln || meta.slug;

    for (const doc of bundle.docs) {
      if (opts.courseFilter !== "all" && doc.c !== opts.courseFilter) continue;

      let bodyHit = false;
      for (const chunk of doc.p) {
        const text = chunk.t;
        if (!chunkMatches(text, q, tokens)) continue;
        bodyHit = true;
        results.push({
          lecturer: meta.slug,
          lecturerName,
          course: doc.c,
          courseTitle: doc.ct,
          sessionId: doc.s,
          sessionTitle: doc.t,
          kind: doc.kind,
          text,
          paraIndex: chunk.i,
          start:
            typeof chunk.start === "number" && Number.isFinite(chunk.start)
              ? chunk.start
              : null,
          site: meta.site,
        });
      }

      if (!bodyHit) {
        const titleBlob = `${doc.t} ${doc.k} ${doc.ct}`.trim();
        if (chunkMatches(titleBlob, q, tokens)) {
          results.push({
            lecturer: meta.slug,
            lecturerName,
            course: doc.c,
            courseTitle: doc.ct,
            sessionId: doc.s,
            sessionTitle: doc.t,
            kind: doc.kind,
            text: doc.k ? `${doc.t} — ${doc.k}` : doc.t,
            paraIndex: -1,
            start: null,
            site: meta.site,
          });
        }
      }
    }
  }

  return results;
}

export function shortLecturerName(name: string): string {
  return name
    .replace(/^حضرت استاد\s+/u, "")
    .replace(/^آیت‌الله\s+/u, "")
    .replace(/^حجت‌الاسلام والمسلمین\s+/u, "")
    .replace(/^حجت‌الاسلام\s+/u, "")
    .trim();
}
