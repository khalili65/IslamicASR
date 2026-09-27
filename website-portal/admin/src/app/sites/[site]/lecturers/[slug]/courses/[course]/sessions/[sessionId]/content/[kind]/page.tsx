import { notFound } from "next/navigation";
import { SessionContentEditor } from "@/components/SessionContentEditor";
import { listSessions, type SessionDocKind } from "@/lib/content";
import { isSiteId } from "@/lib/sites";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{
    site: string;
    slug: string;
    course: string;
    sessionId: string;
    kind: string;
  }>;
};

function parseKind(kind: string): SessionDocKind | null {
  if (kind === "book" || kind === "summary") return kind;
  return null;
}

export default async function SessionContentPage({ params }: Props) {
  const { site: rawSite, slug, course, sessionId, kind: rawKind } =
    await params;
  if (!isSiteId(rawSite)) notFound();
  const kind = parseKind(rawKind);
  if (!kind) notFound();

  const sessions = listSessions(rawSite, slug, course);
  const session = sessions.find((s) => s.id === sessionId);
  if (!session) notFound();

  return (
    <SessionContentEditor
      site={rawSite}
      lecturer={slug}
      course={course}
      sessionId={sessionId}
      sessionTitle={session.title}
      kind={kind}
    />
  );
}
