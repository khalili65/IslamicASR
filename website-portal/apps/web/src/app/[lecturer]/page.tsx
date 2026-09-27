import Link from "next/link";
import { notFound } from "next/navigation";
import { getSiteIndex, toPersianDigits } from "@/lib/data";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  TextIcon,
  WaveIcon,
} from "@/components/Icons";

type Props = {
  params: Promise<{ lecturer: string }>;
};

export function generateStaticParams() {
  const site = getSiteIndex();
  return site.lecturers.map((l) => ({ lecturer: l.slug }));
}

export default async function LecturerPage({ params }: Props) {
  const { lecturer: slug } = await params;
  const site = getSiteIndex();
  const lecturer = site.lecturers.find((l) => l.slug === slug);
  if (!lecturer) notFound();

  const sessions = lecturer.courses.reduce((s, c) => s + c.sessionCount, 0);
  const transcribed = lecturer.courses.reduce(
    (s, c) => s + c.transcribedCount,
    0,
  );

  return (
    <main className="space-y-8">
      <section className="animate-rise card overflow-hidden p-0">
        <div className="flex flex-col sm:flex-row">
          <div className="relative aspect-square shrink-0 overflow-hidden bg-brand/30 sm:w-48 md:w-56">
            {lecturer.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={lecturer.avatar}
                alt={lecturer.name}
                className="h-full w-full object-cover object-center"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-brand-deep to-brand text-5xl font-black text-white/90">
                {lecturer.name.trim().charAt(0) || "م"}
              </div>
            )}
          </div>

          <div className="flex flex-1 flex-col justify-center p-6">
            <Link
              href="/"
              className="inline-flex w-fit items-center gap-1.5 text-xs font-medium text-ink/50 transition hover:text-brand-deep"
            >
              <ArrowRightIcon className="h-3.5 w-3.5" />
              همهٔ مدرسین
            </Link>
            <h1 className="mt-2 text-2xl font-black leading-9 tracking-tight">
              {lecturer.name}
            </h1>
            {lecturer.title ? (
              <p className="mt-1 text-sm font-medium text-brand-deep/85">
                {lecturer.title}
              </p>
            ) : null}
            {lecturer.bio ? (
              <p className="mt-3 text-sm leading-7 text-ink/65">{lecturer.bio}</p>
            ) : null}
            {lecturer.links?.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {lecturer.links.map((link) => (
                  <a
                    key={link.url}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="chip transition hover:bg-brand/40 hover:text-brand-deep"
                  >
                    {link.label}
                  </a>
                ))}
              </div>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="chip">
                <WaveIcon className="h-3.5 w-3.5" />
                {toPersianDigits(lecturer.courses.length)}{" "}
                {lecturer.format === "text" ? "کتاب" : "دوره"}
              </span>
              <span className="chip">
                {toPersianDigits(sessions)}{" "}
                {lecturer.format === "text" ? "فصل" : "جلسه"}
              </span>
              <span className="chip">
                <TextIcon className="h-3.5 w-3.5" />
                {lecturer.format === "text"
                  ? "کتابخانه متنی"
                  : `${toPersianDigits(transcribed)} دارای متن`}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <h2 className="section-title">دوره‌ها</h2>
            <p className="mt-1 text-sm text-ink/50">
              {lecturer.format === "text"
                ? "کتاب‌ها و مجموعه‌های متنی این مدرس"
                : "دوره‌های این مدرس — با افزودن پوشهٔ جدید در آینده اینجا ظاهر می‌شوند"}
            </p>
          </div>
          <span className="chip shrink-0">
            {toPersianDigits(lecturer.courses.length)} دوره
          </span>
        </div>

        {lecturer.courses.length === 0 ? (
          <div className="card px-6 py-12 text-center text-sm text-ink/50">
            هنوز دوره‌ای برای این مدرس ثبت نشده است.
          </div>
        ) : (
          <div className="grid gap-3">
            {lecturer.courses.map((course) => {
              const percent = course.sessionCount
                ? Math.round(
                    (course.transcribedCount / course.sessionCount) * 100,
                  )
                : 0;
              return (
                <Link
                  key={course.slug}
                  href={`/${lecturer.slug}/${course.slug}/`}
                  className="card-link group overflow-hidden p-0"
                >
                  {course.cover ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={course.cover}
                      alt=""
                      className="aspect-[16/9] w-full object-cover object-center"
                    />
                  ) : null}
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <h3 className="text-lg font-bold tracking-tight">
                          {course.title}
                        </h3>
                        {course.description ? (
                          <p className="mt-1 line-clamp-2 text-sm leading-6 text-ink/60">
                            {course.description}
                          </p>
                        ) : null}
                      </div>
                      <span className="mt-1 shrink-0 text-ink/25 transition group-hover:text-brand-deep">
                        <ArrowLeftIcon className="h-5 w-5" />
                      </span>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                      <span className="chip">
                        {toPersianDigits(course.sessionCount)}{" "}
                        {course.format === "text" || lecturer.format === "text"
                          ? "فصل"
                          : "جلسه"}
                      </span>
                      {course.format === "text" || lecturer.format === "text" ? (
                        <span className="chip">
                          <TextIcon className="h-3.5 w-3.5" />
                          متن‌خوانی
                        </span>
                      ) : (
                        <>
                          <span className="chip tabular-nums">
                            {toPersianDigits(course.totalDurationText)}
                          </span>
                          <span className="chip">
                            <TextIcon className="h-3.5 w-3.5" />
                            {toPersianDigits(course.transcribedCount)} دارای متن
                          </span>
                        </>
                      )}
                    </div>

                    {course.format === "text" || lecturer.format === "text" ? null : (
                      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink/[0.07]">
                        <div
                          className="h-full rounded-full bg-brand-deep/70"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
