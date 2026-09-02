/** Persian text normalisation + tokenisation for client search. */

const CHAR_MAP: Record<string, string> = {
  "\u064a": "\u06cc",
  "\u0649": "\u06cc",
  "\u0643": "\u06a9",
  "\u0629": "\u0647",
  "\u0623": "\u0627",
  "\u0625": "\u0627",
  "\u0622": "\u0627",
  "\u0671": "\u0627",
  "\u0624": "\u0648",
  "\u0626": "\u06cc",
  "\u06c0": "\u0647",
  "\u06d5": "\u0647",
};

const STRIP_RE =
  /[\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0653\u0654\u0655\u0670\u0640\u200b\u200c\u200d\u200e\u200f\ufeff]/g;

const PUNCT_RE =
  /[\s.,:;!?؟،؛…"'«»‘’“”()[\]{}<>\-–—_/\\|*#=+~`^$%&@·]+/g;

function mapDigit(ch: string): string {
  const code = ch.charCodeAt(0);
  if (code >= 0x06f0 && code <= 0x06f9) return String(code - 0x06f0);
  if (code >= 0x0660 && code <= 0x0669) return String(code - 0x0660);
  return ch;
}

export function normalizePersian(text: string): string {
  let out = "";
  for (const ch of text.normalize("NFKC")) {
    const mapped = CHAR_MAP[ch] ?? mapDigit(ch);
    out += mapped;
  }
  return out.replace(STRIP_RE, "").replace(PUNCT_RE, "").toLowerCase();
}

export function tokenizePersian(text: string): string[] {
  const tokens: string[] = [];
  for (const raw of text.split(/\s+/)) {
    const norm = normalizePersian(raw);
    if (norm) tokens.push(norm);
  }
  return tokens;
}

/** True when every query token appears somewhere in the haystack tokens/text. */
export function tokensMatch(haystack: string, queryTokens: string[]): boolean {
  if (!queryTokens.length) return false;
  const hay = tokenizePersian(haystack);
  if (!hay.length) return false;
  const set = new Set(hay);
  return queryTokens.every((token) => set.has(token));
}

/** Fallback substring match on normalised collapsed text (for partial words). */
export function normalizedIncludes(haystack: string, needle: string): boolean {
  const h = normalizePersian(haystack.replace(/\s+/g, ""));
  const n = normalizePersian(needle.replace(/\s+/g, ""));
  return n.length >= 2 && h.includes(n);
}
