"""Group timed tokens into subtitle cues and derive chapters from headings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# The reference player uses roughly one sentence per cue at 15-20 seconds.
# These bounds reproduce that feel while keeping lines readable on a phone.
MAX_SECONDS = 20.0
SOFT_SECONDS = 12.0
MIN_SECONDS = 1.5
MAX_CHARS = 140

# Arabic quotations are rendered in a larger face, so fewer characters fit on
# one line and they need breaking sooner than Persian prose.
QUOTE_MAX_CHARS = 90
QUOTE_SOFT_SECONDS = 6.0

_HARD_STOPS = ".؟!۔…؛?"
_SOFT_STOPS = "،:,"

# Raw ASR text carries no editorial punctuation to lean on, so a cue that fills
# up on character count alone breaks mid-phrase: the line flips while the
# speaker is still finishing the thought. Silence between words is the reliable
# boundary, so raw cues are cut at pauses and only fall back to length.
RAW_PAUSE_SECONDS = 0.32
RAW_MAX_SECONDS = 14.0
RAW_MAX_CHARS = 110

_STYLE_RE = re.compile(r"<style>.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_META_PREFIXES = ("یادداشت:", "منبع", "Masaha", "**موضوع:**")
_SPEECH_STARTERS = (
    "این ",
    "ما ",
    "در ",
    "اگر ",
    "اما ",
    "بنابراین",
    "پس ",
    "از ",
    "کسانی ",
    "ان‌شاءالله",
    "انشاالله",
    "خواهش ",
    "همه ",
    "لطفاً",
    "الحمد",
    "وقتی ",
    "اکنون ",
    "بار ",
    "ممکن ",
    "همچنین ",
    "تهیه ",
    "دربارهٔ ",
)


@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str
    kind: str                       # speech | quote
    block: int
    chapter: Optional[int] = None
    translation: Optional[str] = None
    words: List[tuple] = field(default_factory=list)   # (start, end, display)


@dataclass
class Chapter:
    index: int
    title: str
    start: float
    end: float


def build_cues(blocks, timed_by_block) -> tuple:
    """Turn aligned blocks into cues and chapters.

    `blocks`         : list of transcript.Block in reading order
    `timed_by_block` : {block index -> [TimedToken]} for spoken blocks

    Returns (cues, chapters).
    """
    cues: List[Cue] = []
    chapters: List[Chapter] = []
    pending_chapter_title: Optional[str] = None

    for block_index, block in enumerate(blocks):
        if block.kind == "heading":
            # Only level-2 headings mark chapters; the level-1 heading is the
            # lecture title and deeper ones are subsections within a topic.
            if block.level == 2:
                pending_chapter_title = block.text
            continue

        if block.kind == "translation":
            # Attach to the Arabic quotation it explains rather than becoming
            # its own cue, since it was never spoken.
            if cues and cues[-1].kind == "quote":
                cues[-1].translation = _strip_label(block.text)
            continue

        if block.kind not in ("speech", "quote"):
            continue

        tokens = timed_by_block.get(block_index) or []
        if not tokens:
            continue

        if pending_chapter_title is not None:
            chapters.append(
                Chapter(
                    index=len(chapters),
                    title=pending_chapter_title,
                    start=tokens[0].start,
                    end=tokens[-1].end,
                )
            )
            pending_chapter_title = None

        chapter_index = len(chapters) - 1 if chapters else None
        if block.kind == "quote":
            groups = _split_tokens(tokens, QUOTE_MAX_CHARS, QUOTE_SOFT_SECONDS)
        else:
            groups = _split_tokens(tokens, MAX_CHARS, SOFT_SECONDS)
        groups = _enforce_max_duration(groups)

        for group in groups:
            if not group:
                continue
            cues.append(
                Cue(
                    index=len(cues),
                    start=group[0].start,
                    end=max(group[-1].end, group[0].start + MIN_SECONDS * 0.1),
                    text=" ".join(t.display for t in group),
                    kind=block.kind,
                    block=block_index,
                    chapter=chapter_index,
                    words=[(t.start, t.end, t.display) for t in group],
                )
            )

    _extend_chapters(chapters, cues)
    _close_gaps(cues)
    return cues, chapters


def build_book_chapters(book_path: Path, words, cues: List[Cue]) -> List[Chapter]:
    """Time-stamp book.md section titles on the raw ASR word clock."""
    book_text = book_path.read_text(encoding="utf-8")
    sections = _parse_book_sections(book_text)
    if not sections:
        return []

    chapters: List[Chapter] = []
    min_start = words[0].start if words else 0.0
    duration = words[-1].end if words else 0.0

    opening = _opening_chapter_title(book_text)
    if opening and words:
        chapters.append(
            Chapter(index=0, title=opening, start=words[0].start, end=words[0].start)
        )
        min_start = words[0].start + 20.0

    for title, anchor_text in sections:
        if title.startswith("مقدمه"):
            continue
        start, ratio = _align_section_start(words, anchor_text, min_start)
        if start is None or ratio < 0.30:
            continue
        if chapters and start < chapters[-1].start + 20.0:
            continue
        chapters.append(
            Chapter(index=len(chapters), title=title, start=start, end=start)
        )
        min_start = start + 20.0

    if not chapters:
        return []

    _extend_chapters(chapters, cues)
    if chapters[-1].end < duration:
        chapters[-1].end = duration
    return chapters


def _parse_book_sections(text: str) -> List[Tuple[str, str]]:
    """Return (section title, anchor prose) pairs from a *.book.md file."""
    text = _STYLE_RE.sub("", text)
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    sections: List[Tuple[str, str]] = []
    index = 0
    while index < len(chunks):
        chunk = chunks[index]
        if not _is_book_section_title(chunk):
            index += 1
            continue
        body = _next_speech_chunk(chunks, index + 1)
        if body:
            sections.append((chunk, body))
        index += 1
    return sections


def _is_book_section_title(chunk: str) -> bool:
    line = chunk.strip()
    if "\n" in line:
        return False
    if len(line) < 6 or len(line) > 120:
        return False
    if any(line.startswith(prefix) for prefix in _META_PREFIXES):
        return False
    if line.startswith(">") or "<p" in line or line.startswith("|"):
        return False
    if line.endswith("?") or line.endswith("؟"):
        return False
    if line.endswith(".") and len(line) > 70:
        return False
    if any(line.startswith(starter) for starter in _SPEECH_STARTERS):
        return False
    if "http" in line.lower():
        return False
    return True


def _next_speech_chunk(chunks: List[str], start: int) -> Optional[str]:
    for chunk in chunks[start:]:
        if _is_book_section_title(chunk):
            return None
        if chunk.startswith(">"):
            continue
        if "ayah-ar" in chunk or chunk.startswith("<p"):
            continue
        plain = _TAG_RE.sub("", chunk).strip()
        if any(plain.startswith(prefix) for prefix in _META_PREFIXES):
            continue
        if plain.startswith("ترجمه"):
            continue
        if len(plain) >= 20:
            return plain
    return None


def _opening_chapter_title(book_text: str) -> Optional[str]:
    for chunk in re.split(r"\n\s*\n", book_text):
        first_line = chunk.strip().split("\n", 1)[0].strip()
        if first_line in {"آغاز سخن", "افتتاح"}:
            return first_line
    return None


def _align_section_start(words, body: str, min_start: float) -> Tuple[Optional[float], float]:
    from align import align_tokens
    from persian import tokenize

    tokens = tokenize(_TAG_RE.sub("", body))[:80]
    if len(tokens) < 5:
        return None, 0.0

    start_idx = next(
        (index for index, word in enumerate(words) if word.start >= min_start - 0.3),
        0,
    )
    best_ratio = 0.0
    best_start: Optional[float] = None
    step = max(1, len(tokens) // 4)

    for index in range(start_idx, len(words), step):
        if words[index].start > min_start + 900:
            break
        window = words[index : min(index + 1200, len(words))]
        timed, stats = align_tokens(window, tokens)
        if not timed or stats.ratio <= best_ratio:
            continue
        start = timed[0].start
        if start >= min_start - 0.3:
            best_ratio = stats.ratio
            best_start = start
    return best_start, best_ratio


def build_raw_cues(words) -> tuple:
    """Group verbatim ASR word timings into player cues (no alignment step)."""
    from align import TimedToken

    tokens = [
        TimedToken(display=w.text, start=w.start, end=w.end, exact=True)
        for w in words
    ]
    if not tokens:
        return [], []

    groups = _enforce_raw_limits(_split_raw_tokens(tokens))
    cues: List[Cue] = []
    for group in groups:
        if not group:
            continue
        cues.append(
            Cue(
                index=len(cues),
                start=group[0].start,
                end=max(group[-1].end, group[0].start + MIN_SECONDS * 0.1),
                text=" ".join(t.display for t in group),
                kind="speech",
                block=0,
                chapter=None,
                words=[(t.start, t.end, t.display) for t in group],
            )
        )
    _close_gaps(cues)
    return cues, []


def _token_chars(group) -> int:
    from persian import strip_zwnj

    return sum(len(strip_zwnj(t.display)) + 1 for t in group)


def _split_raw_tokens(tokens) -> List[list]:
    """Cut verbatim ASR words into cues at sentence ends and audible pauses."""
    groups: List[list] = []
    current: list = []

    for position, token in enumerate(tokens):
        current.append(token)
        duration = token.end - current[0].start
        last_char = token.display.rstrip()[-1:] if token.display.rstrip() else ""
        gap_after = (
            tokens[position + 1].start - token.end
            if position + 1 < len(tokens)
            else 0.0
        )

        long_enough = duration >= MIN_SECONDS
        if (
            (last_char in _HARD_STOPS and long_enough)
            or (gap_after >= RAW_PAUSE_SECONDS and long_enough)
            or duration >= RAW_MAX_SECONDS
        ):
            groups.append(current)
            current = []

    if current:
        if groups and _token_chars(current) < 25:
            groups[-1].extend(current)
        else:
            groups.append(current)
    return groups


def _split_at_widest_gap(group) -> tuple:
    """Divide an over-long cue at its longest internal silence."""
    margin = max(1, len(group) // 5)
    best_index = None
    best_gap = -1.0
    for index in range(margin, len(group) - margin + 1):
        gap = group[index].start - group[index - 1].end
        if gap > best_gap:
            best_gap = gap
            best_index = index
    if best_index is None:
        best_index = len(group) // 2
    return group[:best_index], group[best_index:]


def _enforce_raw_limits(groups) -> List[list]:
    """Keep raw cues readable, still preferring silence over word count."""
    result: List[list] = []
    queue = list(groups)
    while queue:
        group = queue.pop(0)
        if not group:
            continue
        too_long = group[-1].end - group[0].start > RAW_MAX_SECONDS
        too_wide = _token_chars(group) > RAW_MAX_CHARS
        if len(group) < 4 or not (too_long or too_wide):
            result.append(group)
            continue
        head, tail = _split_at_widest_gap(group)
        queue.insert(0, tail)
        queue.insert(0, head)
    return result


def _split_tokens(tokens, max_chars: int, soft_seconds: float) -> List[list]:
    """Break a block into cues at sentence boundaries."""
    from persian import strip_zwnj

    groups: List[list] = []
    current: list = []
    chars = 0

    for token in tokens:
        current.append(token)
        chars += len(strip_zwnj(token.display)) + 1
        duration = token.end - current[0].start
        last_char = token.display.rstrip()[-1:] if token.display.rstrip() else ""

        hard_stop = last_char in _HARD_STOPS and duration >= MIN_SECONDS
        soft_stop = last_char in _SOFT_STOPS and duration >= soft_seconds
        overflow = duration >= MAX_SECONDS or chars >= max_chars

        if hard_stop or soft_stop or overflow:
            groups.append(current)
            current = []
            chars = 0

    if current:
        # A short trailing fragment reads better merged into the cue before it.
        tail_chars = sum(len(strip_zwnj(t.display)) + 1 for t in current)
        if groups and tail_chars < 25:
            groups[-1].extend(current)
        else:
            groups.append(current)
    return groups


def _enforce_max_duration(groups) -> List[list]:
    """Halve any cue that still runs long.

    A single token can span many seconds when its timing was interpolated
    across a passage the ASR missed, so punctuation alone cannot guarantee the
    duration cap.
    """
    result: List[list] = []
    queue = list(groups)
    while queue:
        group = queue.pop(0)
        if len(group) < 2 or group[-1].end - group[0].start <= MAX_SECONDS:
            result.append(group)
            continue
        midpoint = len(group) // 2
        queue.insert(0, group[midpoint:])
        queue.insert(0, group[:midpoint])
    return result


def _extend_chapters(chapters, cues) -> None:
    """A chapter runs until the next one starts, not just to its first block."""
    for position, chapter in enumerate(chapters):
        if position + 1 < len(chapters):
            chapter.end = chapters[position + 1].start
        elif cues:
            chapter.end = cues[-1].end


def _close_gaps(cues) -> None:
    """Let each cue hold the screen until the next begins.

    Without this, silences between paragraphs would blank the subtitle stage.
    Cues abut exactly so the player never keeps a finished line on screen
    after the next one has started.
    """
    for position, cue in enumerate(cues):
        if position + 1 < len(cues):
            cue.end = cues[position + 1].start
        if cue.end <= cue.start:
            cue.end = cue.start + 0.5
        if cue.end - cue.start > MAX_SECONDS:
            cue.end = cue.start + MAX_SECONDS
            # If clamping created a hole before the next cue, leave it blank
            # rather than holding stale text across a long pause.
            if position + 1 < len(cues) and cue.end > cues[position + 1].start:
                cue.end = cues[position + 1].start


def _strip_label(text: str) -> str:
    """Drop the '**ترجمهٔ فارسی (توسط مدل، نه استاد):**' prefix."""
    marker = ":**"
    if text.startswith("**") and marker in text:
        return text.split(marker, 1)[1].strip()
    return text
