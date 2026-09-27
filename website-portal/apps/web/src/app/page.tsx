import Link from "next/link";
import { getSiteIndex, toPersianDigits } from "@/lib/data";
import { ArrowLeftIcon, WaveIcon } from "@/components/Icons";

export default function HomePage() {
  const site = getSiteIndex();

  if (!site.lecturers?.length) {
    return (
      <main className="card px-6 py-16 text-center text-sm text-ink/60">
        هنوز مدرسی ثبت نشده است. ابتدا محتوا را بسازید.
      </main>
    );
  }

  const totalSessions = site.lecturers.reduce(
    (sum, l) => sum + l.courses.reduce((s, c) => s + c.sessionCount, 0),
    0,
  );
  const totalCourses = site.lecturers.reduce(
    (sum, l) => sum + l.courses.length,
    0,
  );

  return (
    <main className="space-y-10">
      <section className="animate-rise relative overflow-hidden rounded-card border border-white/60 bg-surface/70 px-6 py-10 text-center shadow-card backdrop-blur-sm sm:py-12">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(30rem 16rem at 50% -10%, rgb(var(--brand) / 0.55), transparent 70%)",
          }}
        />
        <div className="relative space-y-3">
          <span className="chip-brand mx-auto">
            <WaveIcon className="h-3.5 w-3.5" />
            مجموعه چندمدرسی
          </span>
          <h1 className="text-3xl font-black leading-tight tracking-tight sm:text-4xl">
            {site.brand?.name || "درس‌گفتارها"}
          </h1>
          {site.brand?.tagline ? (
            <p className="mx-auto max-w-xl text-sm leading-7 text-ink/60">
              {site.brand.tagline}
            </p>
          ) : null}
          <dl className="mx-auto flex max-w-md justify-center divide-x divide-x-reverse divide-ink/10 pt-2">
            {[
              [toPersianDigits(site.lecturers.length), "مدرس"],
              [toPersianDigits(totalCourses), "دوره"],
              [toPersianDigits(totalSessions), "جلسه"],
            ].map(([value, label]) => (
              <div key={label} className="px-5 sm:px-6">
                <dt className="text-xl font-black tabular-nums">{value}</dt>
                <dd className="mt-0.5 text-xs text-ink/50">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section>
        <div className="mb-5 flex items-end justify-between gap-3">
          <div>
            <h2 className="section-title">مدرسین</h2>
            <p className="mt-1 text-sm text-ink/50">
              یک مدرس را انتخاب کنید تا دوره‌های او را ببینید
            </p>
          </div>
          <span className="chip shrink-0">
            {toPersianDigits(site.lecturers.length)} مدرس
          </span>
        </div>

        {/* Scales: 1 col → 2 → 3 as you add more lecturers */}
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {site.lecturers.map((lecturer, i) => {
            const sessions = lecturer.courses.reduce(
              (s, c) => s + c.sessionCount,
              0,
            );
            return (
              <Link
                key={lecturer.slug}
                href={`/${lecturer.slug}/`}
                className="card-link group flex h-full flex-col overflow-hidden p-0"
                style={{ animationDelay: `${Math.min(i, 8) * 40}ms` }}
              >
                <div className="relative aspect-[4/3] overflow-hidden bg-brand/30">
                  {lecturer.avatar ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={lecturer.avatar}
                      alt={lecturer.name}
                      className="h-full w-full object-cover object-center transition duration-500 group-hover:scale-[1.03]"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-brand-deep to-brand text-5xl font-black text-white/90">
                      {lecturer.name.trim().charAt(0) || "م"}
                    </div>
                  )}
                </div>

                <div className="flex flex-1 flex-col p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-lg font-bold leading-8 tracking-tight">
                        {lecturer.name}
                      </h3>
                      {lecturer.title ? (
                        <p className="mt-0.5 text-xs font-medium text-brand-deep/80">
                          {lecturer.title}
                        </p>
                      ) : null}
                    </div>
                    <span className="mt-1 shrink-0 text-ink/25 transition group-hover:text-brand-deep">
                      <ArrowLeftIcon className="h-5 w-5" />
                    </span>
                  </div>

                  {lecturer.bio ? (
                    <p className="mt-3 line-clamp-3 flex-1 text-sm leading-7 text-ink/60">
                      {lecturer.bio}
                    </p>
                  ) : (
                    <p className="mt-3 flex-1 text-sm text-ink/40">
                      معرفی به‌زودی…
                    </p>
                  )}

                  <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                    <span className="chip">
                      {toPersianDigits(lecturer.courses.length)}{" "}
                      {lecturer.format === "text" ? "کتاب" : "دوره"}
                    </span>
                    <span className="chip">
                      {toPersianDigits(sessions)}{" "}
                      {lecturer.format === "text" ? "فصل" : "جلسه"}
                    </span>
                    {lecturer.format === "text" ? (
                      <span className="chip">متن</span>
                    ) : null}
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
