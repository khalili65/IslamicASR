import fs from "fs";
import path from "path";

export type SessionDocKind = "corrected" | "summary";

/** Prefer shipped public/data copies; fall back to Audios via public/audio locally. */
export function loadSessionMarkdown(
  lecturer: string,
  course: string,
  session: string,
  kind: SessionDocKind,
): string | null {
  const dataFile = path.join(
    process.cwd(),
    "public",
    "data",
    lecturer,
    course,
    `${session}.${kind}.md`,
  );
  if (fs.existsSync(dataFile)) {
    return fs.readFileSync(dataFile, "utf8");
  }

  const suffix = kind === "corrected" ? ".corrected.md" : ".summary.md";
  const audioRoot = path.join(process.cwd(), "public", "audio");
  const candidates = [
    path.join(audioRoot, lecturer, course, session),
    path.join(
      audioRoot,
      lecturer[0].toUpperCase() + lecturer.slice(1),
      course,
      session,
    ),
  ];
  for (const dir of candidates) {
    if (!fs.existsSync(dir)) continue;
    const file = fs.readdirSync(dir).find((name) => name.endsWith(suffix));
    if (file) {
      return fs.readFileSync(path.join(dir, file), "utf8");
    }
  }
  return null;
}

export function stripEditorialNoise(md: string): string {
  let text = md
    .replace(/<style>[\s\S]*?<\/style>/gi, "")
    .replace(/^>\s*\*\*یادداشت:[\s\S]*?(?=\n#|\n<style|\n\n#)/m, "");

  // Drop model/source meta blockquotes (not lecture content).
  text = text.replace(/(?:^|\n)(?:>[^\n]*(?:\n|$))+/g, (block) => {
    const body = block.replace(/^>?[ \t]*/gm, "");
    if (
      /این فایل را مدل/.test(body) ||
      (/corrected\.md/.test(body) &&
        /مطالع|لفظی|جلسه نیست|بروید/.test(body))
    ) {
      return "\n";
    }
    return block;
  });

  // Drop trailing "پایان خلاصه — مدل…" footers.
  text = text.replace(/\n\*پایان خلاصه[^*]*\*\s*$/u, "");

  return text.replace(/\n{3,}/g, "\n\n").trim();
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inlineFormat(s: string): string {
  return escapeHtml(s).replace(
    /\*\*(.*?)\*\*/g,
    "<strong>$1</strong>",
  );
}

/** Minimal markdown → HTML for reading views. */
export function markdownToHtml(body: string): string {
  const lines = body.split("\n");
  const out: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith("# ")) {
      out.push(`<h1>${inlineFormat(trimmed.slice(2))}</h1>`);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("## ")) {
      out.push(`<h2>${inlineFormat(trimmed.slice(3))}</h2>`);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("### ")) {
      out.push(`<h3>${inlineFormat(trimmed.slice(4))}</h3>`);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("---")) {
      out.push("<hr/>");
      i += 1;
      continue;
    }

    // GFM-ish table
    if (
      trimmed.includes("|") &&
      i + 1 < lines.length &&
      /^\s*\|?[\s-:|]+\|?\s*$/.test(lines[i + 1])
    ) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes("|")) {
        const row = lines[i]
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((c) => c.trim());
        if (!/^[\s-:|]+$/.test(lines[i].trim())) {
          rows.push(row);
        }
        i += 1;
      }
      if (rows.length) {
        const [head, ...bodyRows] = rows;
        out.push("<table>");
        out.push(
          `<thead><tr>${head.map((c) => `<th>${inlineFormat(c)}</th>`).join("")}</tr></thead>`,
        );
        out.push("<tbody>");
        for (const row of bodyRows) {
          out.push(
            `<tr>${row.map((c) => `<td>${inlineFormat(c)}</td>`).join("")}</tr>`,
          );
        }
        out.push("</tbody></table>");
      }
      continue;
    }

    // Bullet list
    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      out.push(
        `<ul>${items.map((item) => `<li>${inlineFormat(item)}</li>`).join("")}</ul>`,
      );
      continue;
    }

    // Blockquote (possibly multi-line)
    if (trimmed.startsWith(">")) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quote.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      out.push(`<blockquote>${inlineFormat(quote.join(" "))}</blockquote>`);
      continue;
    }

    // Paragraph: gather until blank
    const para: string[] = [];
    while (i < lines.length && lines[i].trim()) {
      const t = lines[i].trim();
      if (
        t.startsWith("#") ||
        t.startsWith("---") ||
        t.startsWith(">") ||
        /^[-*]\s+/.test(t) ||
        (t.includes("|") &&
          i + 1 < lines.length &&
          /^\s*\|?[\s-:|]+\|?\s*$/.test(lines[i + 1]))
      ) {
        break;
      }
      para.push(t);
      i += 1;
    }
    const joined = para.join(" ");
    if (joined.includes("ayah-ar")) {
      const plain = joined.replace(/<[^>]+>/g, "").trim();
      out.push(`<p class="ayah">${escapeHtml(plain)}</p>`);
    } else {
      out.push(`<p>${inlineFormat(joined)}</p>`);
    }
  }

  return out.join("\n");
}

export const articleClassName =
  "card p-6 text-[15px] leading-8 " +
  "[&_blockquote]:my-4 [&_blockquote]:rounded-2xl [&_blockquote]:border-e-2 " +
  "[&_blockquote]:border-brand [&_blockquote]:bg-brand/15 [&_blockquote]:px-4 " +
  "[&_blockquote]:py-3 [&_blockquote]:text-sm [&_blockquote]:text-ink/70 " +
  "[&_h1]:mb-5 [&_h1]:text-2xl [&_h1]:font-black " +
  "[&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-bold " +
  "[&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:font-bold " +
  "[&_hr]:my-6 [&_hr]:border-ink/10 [&_p]:mb-4 " +
  "[&_ul]:mb-4 [&_ul]:list-disc [&_ul]:ps-6 [&_li]:mb-1 " +
  "[&_table]:mb-6 [&_table]:w-full [&_table]:border-collapse [&_table]:text-sm " +
  "[&_th]:border [&_th]:border-ink/10 [&_th]:bg-ink/5 [&_th]:px-3 [&_th]:py-2 [&_th]:text-right " +
  "[&_td]:border [&_td]:border-ink/10 [&_td]:px-3 [&_td]:py-2";
