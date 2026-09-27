import { notFound } from "next/navigation";
import { listSessions, readCourse } from "@/lib/content";
import { isSiteId } from "@/lib/sites";
import { CourseEditor } from "@/components/CourseEditor";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ site: string; slug: string; course: string }>;
};

export default async function CoursePage({ params }: Props) {
  const { site: rawSite, slug, course } = await params;
  if (!isSiteId(rawSite)) notFound();
  let meta;
  try {
    meta = readCourse(rawSite, slug, course);
  } catch {
    notFound();
  }
  const sessions = listSessions(rawSite, slug, course);
  return (
    <CourseEditor
      site={rawSite}
      lecturer={slug}
      course={course}
      initial={meta}
      sessions={sessions}
    />
  );
}
