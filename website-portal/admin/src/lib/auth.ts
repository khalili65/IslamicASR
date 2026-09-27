import { createHmac, timingSafeEqual } from "crypto";
import { cookies } from "next/headers";

const COOKIE = "portal_admin";

function secret(): string {
  return (
    process.env.ADMIN_SESSION_SECRET ||
    process.env.ADMIN_PASSWORD ||
    "change-me"
  );
}

export function sessionToken(): string {
  const pw = process.env.ADMIN_PASSWORD || "";
  return createHmac("sha256", secret()).update(`ok:${pw}`).digest("hex");
}

export function verifyPassword(input: string): boolean {
  const expected = process.env.ADMIN_PASSWORD || "";
  if (!expected) return false;
  const a = Buffer.from(input);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

export async function isAuthenticated(): Promise<boolean> {
  const jar = await cookies();
  const c = jar.get(COOKIE)?.value;
  if (!c) return false;
  const want = sessionToken();
  try {
    const a = Buffer.from(c);
    const b = Buffer.from(want);
    return a.length === b.length && timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

export function cookieOptions() {
  // Only mark Secure when explicitly enabled (HTTPS). Plain http://IP:3002
  // cannot store Secure cookies, so login would appear to succeed then bounce.
  const secure =
    process.env.ADMIN_COOKIE_SECURE === "1" ||
    process.env.ADMIN_COOKIE_SECURE === "true";
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure,
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  };
}

export { COOKIE };
