import { Suspense } from "react";
import { Player } from "@/components/Player";
import { TextReader } from "@/components/TextReader";
import { SeekFromQuery } from "@/components/SeekFromQuery";
import { getCues, getSession, getSiteIndex, listSessions } from "@/lib/data";
import {
  articleClassName,
  loadSessionMarkdown,
  markdownToHtml,
  paragraphsToHtml,
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

export default async function SessionPage({ params }: Props) {
  const { lecturer, course, session } = await params;
  const payload = getSession(lecturer, course, session);
  const textOnly = payload.format === "text";

  if (textOnly && payload.hasFullText) {
    const md = loadSessionMarkdown(lecturer, course, session, "corrected");
    const raw = loadSessionMarkdown(lecturer, course, session, "raw");
    const html = md
      ? markdownToHtml(md)
      : paragraphsToHtml(raw || "متن این فصل هنوز آماده نیست.");
    return (
      <main>
        <TextReader
          session={payload}
          html={html}
          articleClassName={articleClassName}
        />
      </main>
    );
  }

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
