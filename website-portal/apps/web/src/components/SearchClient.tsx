"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { formatClock, toPersianDigits } from "@/lib/format";
import {
  normalizedIncludes,
  tokenizePersian,
  tokensMatch,
} from "@/lib/persian";
import { SearchIcon } from "@/components/Icons";

export type SearchCatalog = {
  v: number;
  lecturers: Array<{
    slug: string;
    name: string;
    format?: "audio" | "text";
    source?: string;
    courses: Array<{
      slug: string;
      title: string;
      format?: "audio" | "text";
    }>;
  }>;
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

type LecturerIndex = {
  v: number;
  l: string;
  ln: string;
  format?: string;
  source?: string;
  docs: SearchDoc[];
};

type Hit = {
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
  source: string;
};

type Props = {
  catalog: SearchCatalog;
};

const PAGE_SIZE = 100;

export function SearchClient({ catalog }: Props) {
  const searchParams = useSearchParams();
  const initialLecturerParam =
    searchParams?.get("lecturer") || searchParams?.get("lib") || "";
  const initialCourseParam = searchParams?.get("course") || "";

  const resolvedInitial = useMemo(() => {
    let lecturer = "all";
    let course = "all";
    if (
      initialLecturerParam &&
      catalog.lecturers.some((l) => l.slug === initialLecturerParam)
    ) {
      lecturer = initialLecturerParam;
    }
    if (initialCourseParam) {
      const owner = catalog.lecturers.find((l) =>
        l.courses.some((c) => c.slug === initialCourseParam),
      );
      if (owner) {
        lecturer = owner.slug;
        course = initialCourseParam;
      }
    }
    return { lecturer, course };
  }, [catalog, initialLecturerParam, initialCourseParam]);

  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [lecturerFilter, setLecturerFilter] = useState(resolvedInitial.lecturer);
  const [courseFilter, setCourseFilter] = useState(resolvedInitial.course);
  const [indexes, setIndexes] = useState<Record<string, LecturerIndex>>({});
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [visible, setVisible] = useState(PAGE_SIZE);
  const [searching, setSearching] = useState(false);

  const coursesForLecturer = useMemo(() => {
    if (lecturerFilter === "all") {
      return catalog.lecturers.flatMap((l) =>
        l.courses.map((c) => ({
          ...c,
          lecturer: l.slug,
          lecturerName: l.name,
        })),
      );
    }
    const lecturer = catalog.lecturers.find((l) => l.slug === lecturerFilter);
    return (lecturer?.courses || []).map((c) => ({
      ...c,
      lecturer: lecturer!.slug,
      lecturerName: lecturer!.name,
    }));
  }, [catalog, lecturerFilter]);

  useEffect(() => {
    // Reset course when lecturer changes if current course is not in scope.
    if (courseFilter === "all") return;
    const ok = coursesForLecturer.some((c) => c.slug === courseFilter);
    if (!ok) setCourseFilter("all");
  }, [lecturerFilter, coursesForLecturer, courseFilter]);

  useEffect(() => {
    setVisible(PAGE_SIZE);
  }, [query, lecturerFilter, courseFilter]);

  const neededLecturers = useMemo(() => {
    if (lecturerFilter !== "all") return [lecturerFilter];
    return catalog.lecturers.map((l) => l.slug);
  }, [catalog, lecturerFilter]);

  useEffect(() => {
    let cancelled = false;
    const missing = neededLecturers.filter((slug) => !indexes[slug]);
    if (!missing.length) return;

    setLoading(true);
    setLoadError(false);
    Promise.all(
      missing.map(async (slug) => {
        const res = await fetch(`/data/search/${slug}.json`);
        if (!res.ok) throw new Error(String(res.status));
        const data = (await res.json()) as LecturerIndex;
        return [slug, data] as const;
      }),
    )
      .then((entries) => {
        if (cancelled) return;
        setIndexes((prev) => {
          const next = { ...prev };
          for (const [slug, data] of entries) next[slug] = data;
          return next;
        });
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError(true);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [neededLecturers, indexes]);

  const runSearch = () => {
    const next = draft.trim();
    if (next.length < 2) {
      setQuery("");
      return;
    }
    // Yield so the button press paints before the heavy scan.
    setSearching(true);
    window.setTimeout(() => {
      setQuery(next);
      setSearching(false);
    }, 0);
  };

  const hits = useMemo(() => {
    const q = query.trim();
    if (q.length < 2) return [] as Hit[];

    const tokens = tokenizePersian(q);
    const results: Hit[] = [];

    for (const slug of neededLecturers) {
      const bundle = indexes[slug];
      if (!bundle) continue;
      const lecturerName =
        catalog.lecturers.find((l) => l.slug === slug)?.name || bundle.ln || slug;
      const sourceLabel =
        bundle.source === "text-library"
          ? "متن کتابخانه"
          : "متن همگام · ASR";

      for (const doc of bundle.docs) {
        if (courseFilter !== "all" && doc.c !== courseFilter) continue;

        let bodyHit = false;
        for (const chunk of doc.p) {
          const text = chunk.t;
          // Match only the snippet body — never the title — so every
          // result card actually contains the query in its text.
          if (!chunkMatches(text, q, tokens)) continue;
          bodyHit = true;
          results.push({
            lecturer: slug,
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
            source: sourceLabel,
          });
        }

        // If only the title/topic matches, show one dedicated hit whose
        // snippet is the title itself (not every paragraph of the chapter).
        if (!bodyHit) {
          const titleBlob = `${doc.t} ${doc.k} ${doc.ct}`.trim();
          if (chunkMatches(titleBlob, q, tokens)) {
            results.push({
              lecturer: slug,
              lecturerName,
              course: doc.c,
              courseTitle: doc.ct,
              sessionId: doc.s,
              sessionTitle: doc.t,
              kind: doc.kind,
              text: doc.k ? `${doc.t} — ${doc.k}` : doc.t,
              paraIndex: -1,
              start: null,
              source: sourceLabel,
            });
          }
        }
      }
    }

    return results;
  }, [query, neededLecturers, indexes, courseFilter, catalog.lecturers]);

  const shown = hits.slice(0, visible);
  const hasQuery = query.trim().length >= 2;

  return (
    <main className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-black tracking-tight">جستجو</h1>
        <p className="text-sm text-ink/55">
          در همهٔ مدرسین و دوره‌ها — فیلتر مدرس و دوره را می‌توانید عوض کنید.
          جلسات صوتی روی متن همگام ASR جستجو می‌شوند (نه نسخهٔ کتابی)؛ کتابخانهٔ
          متنی روی متن فصل‌ها.
        </p>
      </header>

      <div className="space-y-3">
        <div>
          <p className="mb-2 text-xs font-medium text-ink/45">مدرس</p>
          <div className="flex flex-wrap gap-2">
            <FilterChip
              active={lecturerFilter === "all"}
              onClick={() => {
                setLecturerFilter("all");
                setCourseFilter("all");
              }}
              label="همه"
            />
            {catalog.lecturers.map((lecturer) => (
              <FilterChip
                key={lecturer.slug}
                active={lecturerFilter === lecturer.slug}
                onClick={() => {
                  setLecturerFilter(lecturer.slug);
                  setCourseFilter("all");
                }}
                label={shortName(lecturer.name)}
              />
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium text-ink/45">دوره / کتاب</p>
          <div className="flex flex-wrap gap-2">
            <FilterChip
              active={courseFilter === "all"}
              onClick={() => setCourseFilter("all")}
              label="همه"
            />
            {coursesForLecturer.map((course) => (
              <FilterChip
                key={`${course.lecturer}-${course.slug}`}
                active={courseFilter === course.slug}
                onClick={() => {
                  setLecturerFilter(course.lecturer);
                  setCourseFilter(course.slug);
                }}
                label={course.title}
              />
            ))}
          </div>
        </div>
      </div>

      <form
        className="flex flex-col gap-2 sm:flex-row sm:items-stretch"
        onSubmit={(event) => {
          event.preventDefault();
          runSearch();
        }}
      >
        <div className="relative min-w-0 flex-1">
          <SearchIcon className="pointer-events-none absolute end-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink/35" />
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="واژه یا عبارت فارسی…"
            className="w-full rounded-2xl border border-ink/10 bg-surface/90 py-3.5 pe-12 ps-4 text-base shadow-card outline-none transition placeholder:text-ink/35 focus:border-brand-deep"
            autoFocus
          />
        </div>
        <button type="submit" className="btn-primary shrink-0 sm:px-6">
          جستجو
        </button>
      </form>

      {loading ? (
        <p className="text-xs text-ink/50">در حال بارگذاری نمایهٔ جستجو…</p>
      ) : null}
      {loadError ? (
        <p className="text-xs text-accent">بارگذاری نمایهٔ جستجو ناموفق بود.</p>
      ) : null}
      {searching ? (
        <p className="text-xs text-ink/50">در حال جستجو…</p>
      ) : null}

      {hasQuery ? (
        <p className="text-xs text-ink/50">
          {toPersianDigits(hits.length)} نتیجه
          {hits.length > visible
            ? ` · نمایش ${toPersianDigits(visible)} مورد`
            : ""}
        </p>
      ) : (
        <p className="text-xs text-ink/40">
          عبارت را بنویسید و «جستجو» را بزنید (یا Enter). فقط قطعه‌هایی نشان
          داده می‌شوند که خودِ متنشان حاوی واژه باشد.
        </p>
      )}

      <ul className="space-y-2">
        {shown.map((hit) => {
          const href =
            hit.kind === "cue" && hit.start != null
              ? `/${hit.lecturer}/${hit.course}/${hit.sessionId}/?t=${Math.floor(hit.start)}`
              : `/${hit.lecturer}/${hit.course}/${hit.sessionId}/`;
          return (
            <li
              key={`${hit.lecturer}-${hit.course}-${hit.sessionId}-${hit.paraIndex}-${hit.start ?? "x"}`}
            >
              <Link href={href} className="card-link p-4">
                <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2 text-xs text-ink/45">
                  <span className="truncate">
                    {shortName(hit.lecturerName)} · {hit.courseTitle} ·{" "}
                    {hit.sessionTitle}
                  </span>
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className="chip">{hit.source}</span>
                    {hit.start != null ? (
                      <span className="chip tabular-nums">
                        {formatClock(hit.start)}
                      </span>
                    ) : null}
                  </span>
                </div>
                <p className="text-sm leading-7">
                  {highlight(hit.text, query)}
                </p>
              </Link>
            </li>
          );
        })}
      </ul>

      {hasQuery && hits.length > visible ? (
        <button
          type="button"
          className="btn-soft mx-auto block"
          onClick={() => setVisible((n) => n + PAGE_SIZE)}
        >
          نمایش نتایج بیشتر ({toPersianDigits(hits.length - visible)} باقی‌مانده)
        </button>
      ) : null}

      {hasQuery && !hits.length && !loading && !searching ? (
        <p className="card px-6 py-12 text-center text-sm text-ink/50">
          نتیجه‌ای پیدا نشد.
        </p>
      ) : null}
    </main>
  );
}

function FilterChip({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className={`chip ${active ? "chip-brand" : ""}`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function shortName(name: string): string {
  // Keep page chips readable: drop long honorifics when possible.
  return name
    .replace(/^آیت‌الله\s+/u, "")
    .replace(/^حجت‌الاسلام والمسلمین\s+/u, "")
    .replace(/^حجت‌الاسلام\s+/u, "")
    .trim();
}

/** Match only against the given text (snippet body or title blob). */
function chunkMatches(text: string, query: string, tokens: string[]): boolean {
  if (!text) return false;
  if (text.includes(query)) return true;
  if (normalizedIncludes(text, query)) return true;
  if (tokens.length > 0 && tokensMatch(text, tokens)) return true;
  return false;
}

function highlight(text: string, query: string) {
  if (query.length < 2) return text;
  const parts = text.split(query);
  if (parts.length === 1) {
    const token = query.trim().split(/\s+/)[0];
    if (token && token !== query && text.includes(token)) {
      return highlight(text, token);
    }
    return text;
  }
  return parts.flatMap((part, index) =>
    index === 0
      ? [part]
      : [
          <mark
            key={index}
            className="rounded bg-brand/60 px-0.5 text-ink"
          >
            {query}
          </mark>,
          part,
        ],
  );
}
