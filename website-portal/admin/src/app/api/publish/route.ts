import { NextResponse } from "next/server";
import { startPublish } from "@/lib/publish";
import { readPublishStatus } from "@/lib/publish-status";
import { parseSiteId } from "@/lib/sites";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(readPublishStatus());
}

export async function POST(req: Request) {
  let deploy = false;
  let site = parseSiteId(undefined);
  try {
    const body = await req.json();
    deploy = Boolean(body?.deploy);
    site = parseSiteId(body?.site, site);
  } catch {
    /* empty body ok */
  }

  const { started, status } = startPublish({ site, deploy });
  return NextResponse.json(
    { started, status },
    { status: started ? 202 : 409 },
  );
}
