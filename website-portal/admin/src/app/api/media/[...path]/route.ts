import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { pathsFor } from "@/lib/paths";
import { siteFromRequest } from "@/lib/sites";

type Props = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, { params }: Props) {
  const site = siteFromRequest(req);
  const segs = (await params).path;
  const rel = segs.join("/");
  if (rel.includes("..")) {
    return new NextResponse("Forbidden", { status: 403 });
  }
  const root = path.join(pathsFor(site).siteWeb(), "public");
  const file = path.join(root, rel);
  if (!file.startsWith(root) || !fs.existsSync(file)) {
    return new NextResponse("Not found", { status: 404 });
  }
  const data = fs.readFileSync(file);
  const ext = path.extname(file).toLowerCase();
  const type =
    ext === ".jpg" || ext === ".jpeg"
      ? "image/jpeg"
      : ext === ".png"
        ? "image/png"
        : ext === ".webp"
          ? "image/webp"
          : "application/octet-stream";
  return new NextResponse(data, {
    headers: { "Content-Type": type, "Cache-Control": "public, max-age=300" },
  });
}
