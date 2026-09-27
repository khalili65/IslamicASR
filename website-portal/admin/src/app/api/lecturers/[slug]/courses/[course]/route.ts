import { NextResponse } from "next/server";
import { readCourse, writeCourse, type CourseMeta } from "@/lib/content";
import { siteFromRequest } from "@/lib/sites";

type Props = { params: Promise<{ slug: string; course: string }> };

export async function PUT(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug, course } = await params;
  const body = (await req.json()) as CourseMeta;
  writeCourse(site, slug, course, { ...body, slug: course });
  return NextResponse.json({ ok: true });
}

export async function GET(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug, course } = await params;
  return NextResponse.json(readCourse(site, slug, course));
}
