import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { COOKIE, cookieOptions, sessionToken, verifyPassword } from "@/lib/auth";

export async function POST(req: Request) {
  const { password } = await req.json();
  if (!verifyPassword(String(password || ""))) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const jar = await cookies();
  jar.set(COOKIE, sessionToken(), cookieOptions());
  return NextResponse.json({ ok: true });
}
