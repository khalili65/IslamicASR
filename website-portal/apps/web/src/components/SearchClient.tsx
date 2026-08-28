"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { CourseIndex, CuesFile } from "@/lib/types";
import { formatClock, toPersianDigits } from "@/lib/format";
import { SearchIcon } from "@/components/Icons";

type Hit = {
  sessionId: string;
  sessionTitle: string;
  cueIndex: number;
  start: number;
  text: string;
};

type Props = {
  lecturer: string;
  course: string;
  courseTitle: string;
  sessions: CourseIndex["sessions"];
  cueBundles: Record<string, CuesFile>;
};

export function SearchClient({
  lecturer,
  course,
  courseTitle,
  sessions,
  cueBundles,
}: Props) {
  const [q, setQ] = useState("");

  const hits = useMemo(() => {
    const query = q.trim();
    if (query.length < 2) return [] as Hit[];
    const results: Hit[] = [];
    for (const session of sessions) {
      const bundle = cueBundles[session.id];
      if (!bundle) continue;
      for (const cue of bundle.cues) {
        if (cue.text.includes(query)) {
          results.push({
            sessionId: session.id,
            sessionTitle: session.title,
            cueIndex: cue.i,
            start: cue.start,
            text: cue.text,
          });
          if (results.length >= 80) return results;
        }
      }
    }
    return results;
  }, [q, sessions, cueBundles]);

  const query = q.trim();

  return (
    <main className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-black tracking-tight">جستجو</h1>
        <p className="text-sm text-ink/55">در متن جلسات «{courseTitle}»</p>
      </header>

      <div className="relative">
        <SearchIcon className="pointer-events-none absolute end-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink/35" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="عبارت فارسی…"
          className="w-full rounded-2xl border border-ink/10 bg-surface/90 py-3.5 pe-12 ps-4 text-base shadow-card outline-none transition placeholder:text-ink/35 focus:border-brand-deep"
          autoFocus
        />
      </div>

      {query.length >= 2 ? (
        <p className="text-xs text-ink/50">
          {toPersianDigits(hits.length)} نتیجه
          {hits.length >= 80 ? " (نمایش ۸۰ مورد اول)" : ""}
        </p>
      ) : (
        <p className="text-xs text-ink/40">
          برای شروع، دست‌کم دو حرف بنویسید.
        </p>
      )}

      <ul className="space-y-2">
        {hits.map((hit) => (
          <li key={`${hit.sessionId}-${hit.cueIndex}`}>
            <Link
              href={`/${lecturer}/${course}/${hit.sessionId}/?t=${Math.floor(hit.start)}`}
              className="card-link p-4"
            >
              <div className="mb-1.5 flex items-center justify-between gap-2 text-xs text-ink/45">
                <span className="truncate">{hit.sessionTitle}</span>
                <span className="chip tabular-nums">
                  {formatClock(hit.start)}
                </span>
              </div>
              <p className="text-sm leading-7">
                {highlight(hit.text, query)}
              </p>
            </Link>
          </li>
        ))}
      </ul>

      {query.length >= 2 && !hits.length ? (
        <p className="card px-6 py-12 text-center text-sm text-ink/50">
          نتیجه‌ای پیدا نشد.
        </p>
      ) : null}
    </main>
  );
}

/** Wrap each occurrence of the query so the eye lands on it immediately. */
function highlight(text: string, query: string) {
  if (query.length < 2) return text;
  const parts = text.split(query);
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
