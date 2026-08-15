"""Map the corrected transcript onto the raw ASR word timestamps.

The corrected text and the raw ASR text describe the same speech but differ
word by word: fillers were removed, garbled words were fixed, Arabic quotations
were restored. A sequence diff between the two token streams tells us which
corrected token corresponds to which timed raw word; everything else is
interpolated from its neighbours.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional


@dataclass
class TimedToken:
    display: str
    start: float
    end: float
    exact: bool          # True when a raw ASR word supplied the timing


@dataclass
class AlignmentStats:
    total: int
    exact: int
    interpolated: int
    max_gap: float = 0.0      # longest stretch of audio with no exact anchor
    p95_gap: float = 0.0
    drift_fraction: float = 0.0   # share of audio sitting in a loose region

    @property
    def ratio(self) -> float:
        return self.exact / self.total if self.total else 0.0


# A stretch of audio longer than this with no exactly-matched word is where a
# cue boundary could visibly drift.
LOOSE_GAP_SECONDS = 10.0


def _anchor_gaps(timed, audio_start: float, audio_end: float) -> tuple:
    """Measure how far apart the exactly-matched tokens are, in seconds.

    Verbatim word match is a poor quality signal here: an editor rewriting
    colloquial speech into formal Persian changes almost every word without
    making the timing any worse. What actually bounds the error on a cue
    boundary is the distance to the nearest exact anchor, so that is what we
    report — as a worst case, a 95th percentile, and the share of the lecture
    sitting inside a loosely anchored stretch.
    """
    total = max(audio_end - audio_start, 1e-6)
    anchors = [t.start for t in timed if t is not None and t.exact]
    if not anchors:
        return (total, total, 1.0)

    gaps = [anchors[0] - audio_start]
    for previous, current in zip(anchors, anchors[1:]):
        gaps.append(current - previous)
    gaps.append(audio_end - anchors[-1])
    gaps = [g for g in gaps if g >= 0]
    if not gaps:
        return (0.0, 0.0, 0.0)

    loose = sum(g for g in gaps if g > LOOSE_GAP_SECONDS)
    gaps.sort()
    index = min(len(gaps) - 1, int(round(0.95 * (len(gaps) - 1))))
    return (gaps[-1], gaps[index], loose / total)


def align_tokens(words, tokens) -> tuple:
    """Align corrected `tokens` to timed ASR `words`.

    `words`  : list of transcript.Word (start, end, text)
    `tokens` : list of (display, normalized) pairs, in reading order

    Returns (timed_tokens, stats).
    """
    raw_norm = [_normalize_word(w.text) for w in words]
    corrected_norm = [norm for _display, norm in tokens]

    # autojunk would discard the most frequent tokens once the sequence passes
    # 200 elements. In Persian prose that means dropping "که", "را", "به" — the
    # very anchors we need. It must stay off.
    matcher = SequenceMatcher(None, raw_norm, corrected_norm, autojunk=False)

    timed: List[Optional[TimedToken]] = [None] * len(tokens)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(j2 - j1):
                word = words[i1 + offset]
                timed[j1 + offset] = TimedToken(
                    tokens[j1 + offset][0], word.start, word.end, True
                )
        elif tag == "replace":
            # Spread the raw span across the replacement tokens proportionally;
            # the words differ but the region of audio is the same.
            span_words = words[i1:i2]
            count = j2 - j1
            if not span_words or count <= 0:
                continue
            start = span_words[0].start
            end = span_words[-1].end
            step = (end - start) / count if count else 0.0
            for offset in range(count):
                token_start = start + step * offset
                timed[j1 + offset] = TimedToken(
                    tokens[j1 + offset][0],
                    token_start,
                    token_start + step,
                    False,
                )
        # "insert" leaves gaps for the interpolation pass below.
        # "delete" simply means raw words with no corrected counterpart.

    _fill_gaps(timed, tokens, words)
    _enforce_monotonic(timed)

    exact = sum(1 for t in timed if t and t.exact)
    max_gap, p95_gap, drift = _anchor_gaps(timed, words[0].start, words[-1].end)
    stats = AlignmentStats(
        total=len(timed),
        exact=exact,
        interpolated=len(timed) - exact,
        max_gap=max_gap,
        p95_gap=p95_gap,
        drift_fraction=drift,
    )
    return [t for t in timed if t is not None], stats


def _normalize_word(text: str) -> str:
    from persian import normalize

    return normalize(text)


def _fill_gaps(timed, tokens, words) -> None:
    """Give every untimed token a slot between its nearest timed neighbours."""
    if not words:
        return
    audio_start, audio_end = words[0].start, words[-1].end
    index = 0
    total = len(timed)

    while index < total:
        if timed[index] is not None:
            index += 1
            continue

        run_start = index
        while index < total and timed[index] is None:
            index += 1
        run_end = index  # exclusive

        before = timed[run_start - 1].end if run_start > 0 else audio_start
        after = timed[run_end].start if run_end < total else audio_end
        if after < before:
            after = before

        count = run_end - run_start
        step = (after - before) / count if count else 0.0
        for offset in range(count):
            token_start = before + step * offset
            timed[run_start + offset] = TimedToken(
                tokens[run_start + offset][0],
                token_start,
                token_start + step,
                False,
            )


def _enforce_monotonic(timed) -> None:
    """Guarantee non-decreasing times so cue boundaries are always valid."""
    previous = 0.0
    for token in timed:
        if token is None:
            continue
        if token.start < previous:
            token.start = previous
        if token.end < token.start:
            token.end = token.start
        previous = token.start
