import Link from "next/link";
import { getSession, listSessions, getSiteIndex } from "@/lib/data";
import { PlayIcon, TextIcon } from "@/components/Icons";
import {
  articleClassName,
  loadSessionMarkdown,
  markdownToHtml,
  stripEditorialNoise,
} from "@/lib/markdown";

type Props = {
  params: Promise<{ lecturer: string; course: string; session: string }>;
};

export function generateStaticParams() {
  const site = getSiteIndex();
  const params: { lecturer: string; course: string; session: string }[] = [];
  for (const lecturer of site.lecturers) {
    for (const course of lecturer.courses) {
      for (const session of listSessions(lecturer.slug, course.slug)) {
        params.push({
          lecturer: lecturer.slug,
          course: course.slug,
          session,
        });
      }
    }
  }
  return params;
}

export default async function SummaryPage({ params }: Props) {
  const { lecturer, course, session } = await params;
  const payload = getSession(lecturer, course, session);
  const md = loadSessionMarkdown(lecturer, course, session, "summary");
  const body = md
    ? stripEditorialNoise(md)
    : payload.summary || "خلاصه‌ای برای این جلسه موجود نیست.";
  const html = markdownToHtml(body);

  return (
    <main className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href={`/${lecturer}/${course}/${session}/`} className="btn-soft">
          <PlayIcon className="h-4 w-4" />
          بازگشت به پخش
        </Link>
        <div className="flex items-center gap-2">
          <Link
            href={`/${lecturer}/${course}/${session}/text/`}
            className="btn-soft"
          >
            <TextIcon className="h-4 w-4" />
            متن کامل
          </Link>
          <span className="chip">خلاصه · جلسه {payload.id}</span>
        </div>
      </div>
      <article
        className={articleClassName}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </main>
  );
}
