"""Parsers for the two transcript artefacts the ASR pipeline produces.

`NNN_name.txt`          raw ASR text, followed by a `--- Segments ---` block of
                        word-level timestamps.
`NNN_name.corrected.md` the readable edit: headings, speech paragraphs, Arabic
                        quotations, and model-added Farsi translations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SEGMENT_HEADER = "--- Segments ---"
_SEGMENT_RE = re.compile(r"^\[\s*([\d.]+)s\s*-\s*([\d.]+)s\]\s*(.*)$")

_STYLE_RE = re.compile(r"<style>.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")

# A blockquote that announces itself as a model-added translation is text the
# teacher never said, so it must not consume any audio time.
_TRANSLATION_HINTS = ("ترجمهٔ فارسی", "ترجمه فارسی", "توسط مدل", "نه استاد")
_META_PREFIXES = ("**موضوع:**", "**منبع", "**یادداشت", "*یادداشت")

# The editor's closing notes. Everything from this heading to the end of the
# file is commentary about the transcript, not a record of what was said.
_APPENDIX_HEADINGS = ("پی‌نوشت", "پی نوشت", "پینوشت")

# Markdown tables and bullet lists are only ever used for editorial apparatus
# (correction logs, source citations) in these documents.
_LIST_RE = re.compile(r"^\s*([-*+]\s|\d+[.)]\s)")

# Square brackets mark what the teacher did *not* say: stage directions
# ([صدای محیط], [نفس عمیق], [پچ‌پچ]) and clarifications the editor inserted.
# Left in the token stream they claim a share of the audio, which stretches the
# interpolation around them and pushes nearby cues seconds out of sync.
# The negative lookahead keeps Markdown links intact.
_ANNOTATION_RE = re.compile(r"\[[^\]\n]*\](?!\()")

# Blocks whose text was actually spoken aloud and therefore carries timing.
SPOKEN_KINDS = ("speech", "quote")


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Block:
    kind: str                    # heading | speech | quote | translation | note | meta
    text: str
    level: int = 0               # heading depth, 0 otherwise
    tokens: List[tuple] = field(default_factory=list)   # (display, normalized)


def parse_segments(path: Path) -> List[Word]:
    """Read word-level timestamps from the `--- Segments ---` block."""
    words: List[Word] = []
    in_segments = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not in_segments:
            if line.strip() == SEGMENT_HEADER:
                in_segments = True
            continue
        match = _SEGMENT_RE.match(line.strip())
        if not match:
            continue
        start, end, text = match.groups()
        text = text.strip()
        if text:
            words.append(Word(float(start), float(end), text))

    # The ASR occasionally emits a word whose end precedes its start, or a
    # chunk boundary that steps backwards. Clamp so times only move forward.
    previous_end = 0.0
    for word in words:
        if word.start < previous_end:
            word.start = previous_end
        if word.end < word.start:
            word.end = word.start
        previous_end = word.end
    return words


def parse_raw_text(path: Path) -> str:
    """The plain transcript above the segments block."""
    text = path.read_text(encoding="utf-8")
    head, _, _ = text.partition(SEGMENT_HEADER)
    return head.strip()


def _strip_annotations(text: str) -> str:
    """Drop bracketed asides and tidy the whitespace they leave behind."""
    without = _ANNOTATION_RE.sub(" ", text)
    without = re.sub(r"\s+([،.؛:؟!])", r"\1", without)
    return re.sub(r"[ \t]{2,}", " ", without).strip()


def _classify(chunk: str) -> Optional[Block]:
    stripped = chunk.strip()
    if not stripped or stripped in {"---", "***", "___"}:
        return None

    heading = _HEADING_RE.match(stripped)
    if heading:
        hashes, title = heading.groups()
        return Block(kind="heading", text=title.strip(), level=len(hashes))

    if stripped.startswith(">"):
        body = "\n".join(
            line.lstrip("> ").rstrip() for line in stripped.splitlines()
        ).strip()
        kind = "translation" if any(h in body for h in _TRANSLATION_HINTS) else "note"
        return Block(kind=kind, text=body)

    if "ayah-ar" in stripped or stripped.startswith("<p"):
        body = _strip_annotations(_TAG_RE.sub("", stripped))
        if not body:
            return None
        return Block(kind="quote", text=body)

    if any(stripped.startswith(p) for p in _META_PREFIXES):
        return Block(kind="meta", text=stripped)

    if stripped.startswith("|") or _LIST_RE.match(stripped):
        return Block(kind="note", text=stripped)

    body = _strip_annotations(_TAG_RE.sub("", stripped))
    if not body:
        return None
    return Block(kind="speech", text=body)


def parse_corrected(path: Path) -> List[Block]:
    """Split the corrected Markdown into typed blocks, in reading order."""
    from persian import tokenize

    text = _STYLE_RE.sub("", path.read_text(encoding="utf-8"))
    blocks: List[Block] = []
    for chunk in re.split(r"\n\s*\n", text):
        block = _classify(chunk)
        if block is None:
            continue
        if block.kind == "heading" and any(
            marker in block.text for marker in _APPENDIX_HEADINGS
        ):
            break
        if block.kind in SPOKEN_KINDS:
            block.tokens = tokenize(block.text)
            if not block.tokens:
                continue
        blocks.append(block)
    return blocks


def parse_cleaned(path: Path) -> List[Block]:
    """Fallback source: cleaned paragraphs, all treated as speech."""
    from persian import tokenize

    blocks: List[Block] = []
    for chunk in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
        stripped = chunk.strip()
        if not stripped:
            continue
        block = Block(kind="speech", text=stripped, tokens=tokenize(stripped))
        if block.tokens:
            blocks.append(block)
    return blocks
