"""Group timed tokens into subtitle cues and derive chapters from headings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

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
