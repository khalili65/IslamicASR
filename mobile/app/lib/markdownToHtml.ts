/** Minimal markdown + passthrough HTML → HTML for mobile reading. */

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inlineFormat(s: string): string {
  return escapeHtml(s).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

/**
 * Convert book/summary markdown (with embedded ayah HTML) into HTML.
 * Raw HTML blocks (e.g. `<p class="ayah-ar">…</p>`) are kept intact.
 */
export function markdownToHtml(body: string): string {
  const lines = body.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const trimmed = lines[i].trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    // Preserve multi-line HTML blocks (ayah cards, etc.)
    if (trimmed.startsWith("<")) {
      const chunk: string[] = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        if (!t) {
          if (chunk.length) break;
          i += 1;
          continue;
        }
        if (/^#{1,6}\s/.test(t) && !t.startsWith("<")) break;
        chunk.push(lines[i]);
        i += 1;
        // Stop after a closing block tag when next line is blank or markdown
        const joined = chunk.join("\n");
        if (/<\/(p|div|blockquote|ul|ol|table)>\s*$/i.test(joined)) {
          const next = lines[i]?.trim() ?? "";
          if (!next || next.startsWith("#") || next.startsWith(">") || !next.startsWith("<")) {
            break;
          }
        }
      }
      out.push(chunk.join("\n"));
      continue;
    }

    if (/^#{1,6}\s/.test(trimmed)) {
      const level = Math.min(trimmed.match(/^#+/)![0].length, 4);
      const text = trimmed.replace(/^#{1,6}\s+/, "");
      out.push(`<h${level}>${inlineFormat(text)}</h${level}>`);
      i += 1;
      continue;
    }

    if (trimmed.startsWith("---")) {
      out.push("<hr/>");
      i += 1;
      continue;
    }

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

    if (trimmed.startsWith(">")) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quote.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      out.push(`<blockquote>${inlineFormat(quote.join(" "))}</blockquote>`);
      continue;
    }

    const para: string[] = [];
    while (i < lines.length && lines[i].trim()) {
      const t = lines[i].trim();
      if (
        t.startsWith("<") ||
        t.startsWith("#") ||
        t.startsWith("---") ||
        t.startsWith(">") ||
        /^[-*]\s+/.test(t)
      ) {
        break;
      }
      para.push(t);
      i += 1;
    }
    if (!para.length) {
      i += 1;
      continue;
    }
    out.push(`<p>${inlineFormat(para.join(" "))}</p>`);
  }

  return out.join("\n");
}
