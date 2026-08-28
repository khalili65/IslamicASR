import Image from "next/image";
import Link from "next/link";
import { getCourse, getSiteIndex, toPersianDigits } from "@/lib/data";
import {
  ArrowRightIcon,
  PlayIcon,
  SearchIcon,
  TextIcon,
  WaveIcon,
} from "@/components/Icons";

type Props = {
  params: Promise<{ lecturer: string; course: string }>;
};

export function generateStaticParams() {
  const site = getSiteIndex();
  return site.lecturers.flatMap((l) =>
    l.courses.map((c) => ({ lecturer: l.slug, course: c.slug })),
  );
}

export default async function CoursePage({ params }: Props) {
  const { lecturer, course } = await params;
  const data = getCourse(lecturer, course);

  return (
    <main className="space-y-6">
      {data.cover ? (
        <div className="animate-rise overflow-hidden rounded-card border border-white/60 shadow-card">
          <Image
            src={data.cover}
            alt={data.title}
            width={1672}
            height={941}
            priority
            className="h-auto w-full object-cover object-center"
            sizes="(max-width: 768px) 100vw, 768px"
          />
        </div>
      ) : null}

      <section className="animate-rise card p-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink/50 transition hover:text-brand-deep"
        >
          <ArrowRightIcon className="h-3.5 w-3.5" />
          خانه
        </Link>
        <h1 className="mt-2 text-2xl font-black leading-9 tracking-tight">
          {data.title}
        </h1>
        {data.description ? (
          <p className="mt-2 text-sm leading-7 text-ink/60">{data.description}</p>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="chip">
            <WaveIcon className="h-3.5 w-3.5" />
            {toPersianDigits(data.sessionCount)} جلسه
          </span>
          <span className="chip">
            <TextIcon className="h-3.5 w-3.5" />
            {toPersianDigits(data.transcribedCount)} دارای متن
          </span>
          <span className="chip tabular-nums">
            {toPersianDigits(data.totalDurationText)}
          </span>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link
            href={`/${lecturer}/${course}/${data.sessions[0]?.id || "001"}/`}
            className="btn-primary"
          >
            <PlayIcon className="h-4 w-4" />
            شروع دوره
          </Link>
          <Link href="/search/" className="btn-soft">
            <SearchIcon className="h-4 w-4" />
            جستجو در متن
          </Link>
        </div>
      </section>

      <section>
        <h2 className="section-title mb-3">جلسات</h2>
        <ul className="space-y-2">
          {data.sessions.map((s) => (
            <li key={s.id}>
              <Link
                href={`/${lecturer}/${course}/${s.id}/`}
                className="card-link group flex items-center gap-4 px-4 py-3.5"
              >
                <span
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-sm font-black tabular-nums transition ${
                    s.hasTranscript
                      ? "bg-brand/45 text-brand-deep group-hover:bg-brand-deep group-hover:text-white"
                      : "bg-ink/[0.05] text-ink/40"
                  }`}
                >
                  {toPersianDigits(s.index)}
                </span>

                <div className="min-w-0 flex-1">
                  <h3 className="line-clamp-2 font-semibold leading-6">
                    {s.title}
                  </h3>
                  <div className="mt-1 flex items-center gap-2 text-xs text-ink/45">
                    <span className="tabular-nums">
                      {s.durationText ? toPersianDigits(s.durationText) : "—"}
                    </span>
                    <span>·</span>
                    <span
                      className={
                        s.hasTranscript ? "text-brand-deep" : "text-ink/40"
                      }
                    >
                      {s.hasTranscript ? "متن همگام" : "فقط صوت"}
                    </span>
                  </div>
                  {s.topic ? (
                    <p className="mt-1 line-clamp-1 text-xs text-ink/45">
                      {s.topic.replace(/\*\*/g, "")}
                    </p>
                  ) : null}
                </div>

                <span className="shrink-0 text-ink/20 transition group-hover:text-brand-deep">
                  <PlayIcon className="h-5 w-5" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
