"""Parse Manaee/Bayat-style ASR .txt: prose + optional --- Segments --- word times."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SEG_RE = re.compile(
    r"^\[\s*([0-9]+(?:\.[0-9]+)?)\s*s\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*s\]\s*(.*)$"
)
SEP = "--- Segments ---"


@dataclass
class WordTime:
    word: str
    t0: float
    t1: float
    char_start: int
    char_end: int


@dataclass
class ParsedTranscript:
    prose: str
    words: list[WordTime]
    path: Path


def _align_words(prose: str, raw_words: list[tuple[str, float, float]]) -> list[WordTime]:
    """Greedy left-to-right match of ASR tokens into prose character offsets."""
    out: list[WordTime] = []
    cursor = 0
    lower = prose  # Farsi: casefold not critical
    for token, t0, t1 in raw_words:
        clean = token.strip()
        if not clean:
            continue
        # Prefer exact token; fall back to stripping punctuation for search
        needle = clean
        idx = lower.find(needle, cursor)
        if idx < 0:
            stripped = re.sub(r"^[^\w\u0600-\u06FF]+|[^\w\u0600-\u06FF]+$", "", clean)
            if stripped:
                idx = lower.find(stripped, cursor)
                needle = stripped
        if idx < 0:
            # Unmatched token — skip alignment but keep progressing lightly
            continue
        end = idx + len(needle)
        out.append(WordTime(word=clean, t0=t0, t1=t1, char_start=idx, char_end=end))
        cursor = end
    return out


def parse_transcript_file(path: Path) -> ParsedTranscript:
    text = path.read_text(encoding="utf-8", errors="replace")
    if SEP in text:
        prose, seg = text.split(SEP, 1)
    else:
        prose, seg = text, ""
    prose = prose.strip()
    raw_words: list[tuple[str, float, float]] = []
    for line in seg.splitlines():
        m = SEG_RE.match(line.strip())
        if not m:
            continue
        t0, t1, w = float(m.group(1)), float(m.group(2)), m.group(3).strip()
        if w:
            raw_words.append((w, t0, t1))
    words = _align_words(prose, raw_words) if raw_words else []
    return ParsedTranscript(prose=prose, words=words, path=path)


def times_for_span(
    words: list[WordTime], char_start: int, char_end: int
) -> tuple[float | None, float | None]:
    covering = [w for w in words if w.char_end > char_start and w.char_start < char_end]
    if not covering:
        return None, None
    return covering[0].t0, covering[-1].t1
