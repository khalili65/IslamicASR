import { NextResponse } from "next/server";
import { readLecturer, saveLecturerAvatar } from "@/lib/content";
import { siteFromRequest } from "@/lib/sites";

type Props = { params: Promise<{ slug: string }> };

export async function POST(req: Request, { params }: Props) {
  const site = siteFromRequest(req);
  const { slug } = await params;
  readLecturer(site, slug);

  const form = await req.formData();
  const file = form.get("file");
  if (!(file instanceof Blob)) {
    return NextResponse.json({ error: "No file" }, { status: 400 });
  }
  const name = (file as File).name || "avatar.jpg";
  const ext = name.match(/\.(jpe?g|png|webp)$/i)?.[0]?.toLowerCase() || ".jpg";
  const buffer = Buffer.from(await file.arrayBuffer());
  const avatar = saveLecturerAvatar(site, slug, buffer, ext);
  return NextResponse.json({ avatar });
}
