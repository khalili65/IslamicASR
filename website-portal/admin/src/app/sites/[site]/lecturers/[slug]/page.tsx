import { notFound } from "next/navigation";
import { listCourses, readLecturer } from "@/lib/content";
import { isSiteId } from "@/lib/sites";
import { LecturerEditor } from "@/components/LecturerEditor";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ site: string; slug: string }> };

export default async function LecturerPage({ params }: Props) {
  const { site: rawSite, slug } = await params;
  if (!isSiteId(rawSite)) notFound();
  let lec;
  try {
    lec = readLecturer(rawSite, slug);
  } catch {
    notFound();
  }
  const courses = listCourses(rawSite, slug);
  return (
    <LecturerEditor
      site={rawSite}
      slug={slug}
      initial={lec}
      courses={courses}
    />
  );
}
