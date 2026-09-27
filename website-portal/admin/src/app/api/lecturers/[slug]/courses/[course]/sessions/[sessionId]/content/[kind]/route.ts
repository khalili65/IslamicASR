import { NextResponse } from "next/server";
import {
  readSessionDoc,
  writeSessionDoc,
  type SessionDocKind,
} from "@/lib/content";
import { siteFromRequest } from "@/lib/sites";

type Props = {
  params: Promise<{
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

export async function GET(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug, course, sessionId, kind: rawKind } = await params;
  const kind = parseKind(rawKind);
  if (!kind) {
    return NextResponse.json({ error: "Invalid kind" }, { status: 400 });
  }

  const doc = readSessionDoc(site, slug, course, sessionId, kind);
  if (!doc.path) {
    return NextResponse.json(
      { error: "فایل محتوا پیدا نشد." },
      { status: 404 },
    );
  }

  return NextResponse.json({
    content: doc.content,
    path: doc.path,
    writable: doc.writable,
  });
}

export async function PUT(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug, course, sessionId, kind: rawKind } = await params;
  const kind = parseKind(rawKind);
  if (!kind) {
    return NextResponse.json({ error: "Invalid kind" }, { status: 400 });
  }

  const body = await req.json();
  if (typeof body.content !== "string") {
    return NextResponse.json({ error: "Missing content" }, { status: 400 });
  }

  try {
    const savedPath = writeSessionDoc(
      site,
      slug,
      course,
      sessionId,
      kind,
      body.content,
    );
    return NextResponse.json({ ok: true, path: savedPath });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Save failed";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
