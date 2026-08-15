import { Suspense } from "react";
import { Player } from "@/components/Player";
import { SeekFromQuery } from "@/components/SeekFromQuery";
import { getCues, getSession, getSiteIndex, listSessions } from "@/lib/data";

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

export default async function SessionPage({ params }: Props) {
  const { lecturer, course, session } = await params;
  const payload = getSession(lecturer, course, session);
  const cuesFile = getCues(lecturer, course, session);

  return (
    <main>
      <Suspense fallback={null}>
        <SeekFromQuery />
      </Suspense>
      <Player
        session={payload}
        cues={cuesFile?.cues || []}
        cuesPath={
          payload.subtitles?.fa?.cues
            ? `/data/${lecturer}/${course}/${payload.subtitles.fa.cues}`
            : ""
        }
      />
    </main>
  );
}
