import Link from "next/link";
import { getSiteIndex, toPersianDigits } from "@/lib/data";
import { ArrowLeftIcon, PlayIcon, TextIcon, WaveIcon } from "@/components/Icons";

export default function HomePage() {
  const site = getSiteIndex();
  const lecturer =
    site.lecturers.find((l) => l.slug === site.defaultLecturer) ||
    site.lecturers[0];

  if (!lecturer) {
    return (
      <main className="card px-6 py-16 text-center text-sm text-ink/60">
        هنوز دوره‌ای ثبت نشده است. ابتدا محتوا را بسازید.
      </main>
    );
  }

  const sessionCount = lecturer.courses.reduce(
    (sum, c) => sum + c.sessionCount,
    0,
  );
  const transcribedCount = lecturer.courses.reduce(
    (sum, c) => sum + c.transcribedCount,
    0,
  );
  const firstCourse = lecturer.courses[0];

  return (
    <main className="space-y-10">
      {/* Hero */}
      <section className="animate-rise relative overflow-hidden rounded-card border border-white/60 bg-surface/70 px-6 py-12 text-center shadow-card backdrop-blur-sm">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(30rem 16rem at 50% -10%, rgb(var(--brand) / 0.55), transparent 70%)",
          }}
        />
        <div className="relative space-y-4">
          <span className="chip-brand mx-auto">
            <WaveIcon className="h-3.5 w-3.5" />
            {lecturer.title || "مجموعه درس‌گفتارها"}
          </span>
          <h1 className="text-3xl font-black leading-tight tracking-tight sm:text-4xl">
            {site.brand?.name || lecturer.name}
          </h1>
          {lecturer.bio ? (
            <p className="mx-auto max-w-xl text-sm leading-7 text-ink/60">
              {lecturer.bio}
            </p>
          ) : null}
          <dl className="mx-auto flex max-w-md justify-center divide-x divide-x-reverse divide-ink/10 pt-2">
            {[
              [toPersianDigits(sessionCount), "جلسه"],
              [toPersianDigits(transcribedCount), "دارای متن"],
              [toPersianDigits(lecturer.courses.length), "دوره"],
            ].map(([value, label]) => (
              <div key={label} className="px-6">
                <dt className="text-xl font-black tabular-nums">{value}</dt>
                <dd className="mt-0.5 text-xs text-ink/50">{label}</dd>
              </div>
            ))}
          </dl>
          {firstCourse ? (
            <div className="pt-3">
              <Link
                href={`/${lecturer.slug}/${firstCourse.slug}/001/`}
                className="btn-primary px-6 py-3"
              >
                <PlayIcon className="h-4 w-4" />
                پخش اولین جلسه
              </Link>
            </div>
          ) : null}
        </div>
      </section>

      {/* Courses */}
      <section>
        <div className="mb-4 flex items-end justify-between">
          <h2 className="section-title">دوره‌ها</h2>
          <span className="chip">
            {toPersianDigits(lecturer.courses.length)} دوره
          </span>
        </div>
        <div className="grid gap-3">
          {lecturer.courses.map((course) => {
            const percent = course.sessionCount
              ? Math.round((course.transcribedCount / course.sessionCount) * 100)
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
                      {toPersianDigits(course.sessionCount)} جلسه
                    </span>
                    <span className="chip tabular-nums">
                      {toPersianDigits(course.totalDurationText)}
                    </span>
                    <span className="chip">
                      <TextIcon className="h-3.5 w-3.5" />
                      {toPersianDigits(course.transcribedCount)} دارای متن
                    </span>
                  </div>

                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink/[0.07]">
                    <div
                      className="h-full rounded-full bg-brand-deep/70"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </main>
  );
}
