import { NextResponse } from "next/server";
import { readLecturer, writeLecturer, type LecturerMeta } from "@/lib/content";
import { siteFromRequest } from "@/lib/sites";

type Props = { params: Promise<{ slug: string }> };

export async function PUT(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug } = await params;
  const body = (await req.json()) as LecturerMeta;
  writeLecturer(site, slug, { ...body, slug });
  return NextResponse.json({ ok: true });
}

export async function GET(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug } = await params;
  return NextResponse.json(readLecturer(site, slug));
}
