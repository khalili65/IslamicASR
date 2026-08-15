import { getCourse, getCues, getSiteIndex } from "@/lib/data";
import { SearchClient } from "@/components/SearchClient";
import type { CuesFile } from "@/lib/types";

export default function SearchPage() {
  const site = getSiteIndex();
  const lecturer =
    site.lecturers.find((l) => l.slug === site.defaultLecturer) ||
    site.lecturers[0];
  const courseMeta = lecturer?.courses[0];
  if (!lecturer || !courseMeta) {
    return <main className="py-10 text-center">دوره‌ای یافت نشد.</main>;
  }

  const course = getCourse(lecturer.slug, courseMeta.slug);
  const cueBundles: Record<string, CuesFile> = {};
  for (const session of course.sessions) {
    if (!session.hasTranscript) continue;
    const cues = getCues(lecturer.slug, courseMeta.slug, session.id);
    if (cues) cueBundles[session.id] = cues;
  }

  return (
    <SearchClient
      lecturer={lecturer.slug}
      course={courseMeta.slug}
      courseTitle={course.title}
      sessions={course.sessions}
      cueBundles={cueBundles}
    />
  );
}
