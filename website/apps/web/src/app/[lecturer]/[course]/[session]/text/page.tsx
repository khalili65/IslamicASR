import Link from "next/link";
import fs from "fs";
import path from "path";
import { getSession, listSessions, getSiteIndex } from "@/lib/data";
import { PlayIcon } from "@/components/Icons";

type Props = {
  params: Promise<{ lecturer: string; course: string; session: string }>;
};

export function generateStaticParams() {
  const site = getSiteIndex();
  const params: { lecturer: string; course: string; session: string }[] = [];
  for (const lecturer of site.lecturers) {
    for (const course of lecturer.courses) {
      for (const session of listSessions(lecturer.slug, course.slug)) {
        params.push({
          lecturer: lecturer.slug,
          course: course.slug,
          session,
        });
      }
    }
  }
  return params;
}

function loadCorrectedMarkdown(
  lecturer: string,
  course: string,
  session: string,
): string | null {
  // Prefer reading from Audios via the public/audio symlink.
  const audioRoot = path.join(process.cwd(), "public", "audio");
  // Folder names may differ in case (Bayat vs bayat).
  const candidates = [
    path.join(audioRoot, lecturer, course, session),
    path.join(audioRoot, lecturer[0].toUpperCase() + lecturer.slice(1), course, session),
  ];
  for (const dir of candidates) {
    if (!fs.existsSync(dir)) continue;
    const file = fs
      .readdirSync(dir)
      .find((name) => name.endsWith(".corrected.md"));
    if (file) {
      return fs.readFileSync(path.join(dir, file), "utf8");
    }
  }
  return null;
}

function stripFrontMatter(md: string): string {
  return md
    .replace(/<style>[\s\S]*?<\/style>/gi, "")
    .replace(/^>\s*\*\*یادداشت:[\s\S]*?(?=\n#|\n<style|\n\n#)/m, "")
    .trim();
}

export default async function TextPage({ params }: Props) {
  const { lecturer, course, session } = await params;
  const payload = getSession(lecturer, course, session);
  const md = loadCorrectedMarkdown(lecturer, course, session);
  const body = md ? stripFrontMatter(md) : payload.summary || "متنی موجود نیست.";

  // Minimal markdown → HTML for reading (headings + paragraphs).
  const html = body
    .split(/\n\s*\n/)
    .map((chunk) => {
      const t = chunk.trim();
      if (!t) return "";
      if (t.startsWith("# ")) return `<h1>${t.slice(2)}</h1>`;
      if (t.startsWith("## ")) return `<h2>${t.slice(3)}</h2>`;
      if (t.startsWith("### ")) return `<h3>${t.slice(4)}</h3>`;
      if (t.includes("ayah-ar")) {
        const plain = t.replace(/<[^>]+>/g, "").trim();
        return `<p class="ayah">${plain}</p>`;
      }
      if (t.startsWith(">")) {
        return `<blockquote>${t.replace(/^>\s?/gm, "")}</blockquote>`;
      }
      if (t.startsWith("---")) return "<hr/>";
      return `<p>${t.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")}</p>`;
    })
    .join("\n");

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Link href={`/${lecturer}/${course}/${session}/`} className="btn-soft">
          <PlayIcon className="h-4 w-4" />
          بازگشت به پخش
        </Link>
        <span className="chip">جلسه {payload.id}</span>
      </div>
      <article
        className="card p-6 text-[15px] leading-8 [&_blockquote]:my-4 [&_blockquote]:rounded-2xl [&_blockquote]:border-e-2 [&_blockquote]:border-brand [&_blockquote]:bg-brand/15 [&_blockquote]:px-4 [&_blockquote]:py-3 [&_blockquote]:text-sm [&_blockquote]:text-ink/70 [&_h1]:mb-5 [&_h1]:text-2xl [&_h1]:font-black [&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-bold [&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:font-bold [&_hr]:my-6 [&_hr]:border-ink/10 [&_p]:mb-4"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </main>
  );
}
