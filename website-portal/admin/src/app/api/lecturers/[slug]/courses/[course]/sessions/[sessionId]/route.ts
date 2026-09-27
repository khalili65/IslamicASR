import { NextResponse } from "next/server";
import {
  listSessions,
  setSessionHidden,
  setSessionTitle,
} from "@/lib/content";
import { siteFromRequest } from "@/lib/sites";

type Props = {
  params: Promise<{ slug: string; course: string; sessionId: string }>;
};

export async function PATCH(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug, course, sessionId } = await params;
  const body = await req.json();
  if (typeof body.title === "string") {
    setSessionTitle(site, slug, course, sessionId, body.title);
  }
  if (typeof body.hidden === "boolean") {
    setSessionHidden(site, slug, course, sessionId, body.hidden);
  }
  return NextResponse.json({ sessions: listSessions(site, slug, course) });
}
