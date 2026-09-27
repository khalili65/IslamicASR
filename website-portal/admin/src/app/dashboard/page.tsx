import Link from "next/link";
import { listCourses, listLecturers, readLecturer } from "@/lib/content";
import { SITE_IDS, SITES, mediaUrl } from "@/lib/sites";
import { PublishButton } from "@/components/PublishButton";
import { LogoutButton } from "@/components/LogoutButton";

export const dynamic = "force-dynamic";

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-3xl space-y-10 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black">مدیریت محتوا</h1>
          <p className="text-sm text-ink/55">
            ویرایش website و website-portal از یک جا
          </p>
        </div>
        <LogoutButton />
      </header>

      {SITE_IDS.map((siteId) => {
        const site = SITES[siteId];
        const lecturers = listLecturers(siteId);
        return (
          <section key={siteId} className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 pb-3">
              <div>
                <h2 className="text-lg font-black">{site.label}</h2>
                <p className="text-xs text-ink/45 font-mono">{siteId}</p>
              </div>
              <PublishButton site={siteId} />
            </div>

            {lecturers.length === 0 ? (
              <p className="text-sm text-ink/45">محتوایی در این سایت نیست.</p>
            ) : (
              <ul className="space-y-3">
                {lecturers.map((slug) => {
                  const lec = readLecturer(siteId, slug);
                  const courses = listCourses(siteId, slug);
                  const avatar = mediaUrl(siteId, lec.avatar);
                  return (
                    <li key={`${siteId}-${slug}`} className="card p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex gap-3">
                          {avatar ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={avatar}
                              alt=""
                              className="h-14 w-14 rounded-2xl object-cover"
                            />
                          ) : (
                            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand/40 text-lg font-bold">
                              {lec.name.charAt(0)}
                            </span>
                          )}
                          <div>
                            <Link
                              href={`/sites/${siteId}/lecturers/${slug}`}
                              className="font-bold hover:text-brand-deep"
                            >
                              {lec.name}
                            </Link>
                            <p className="text-sm text-ink/55">{lec.title}</p>
                          </div>
                        </div>
                        <Link
                          href={`/sites/${siteId}/lecturers/${slug}`}
                          className="btn-soft text-xs"
                        >
                          ویرایش
                        </Link>
                      </div>
                      <ul className="mt-4 space-y-1 border-t border-ink/5 pt-3">
                        {courses.map((c) => (
                          <li key={c}>
                            <Link
                              href={`/sites/${siteId}/lecturers/${slug}/courses/${c}`}
                              className="block rounded-lg px-2 py-1.5 text-sm hover:bg-brand/20"
                            >
                              {c}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        );
      })}
    </main>
  );
}
