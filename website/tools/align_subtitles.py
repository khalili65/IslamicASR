#!/usr/bin/env python3
"""Produce time-synced subtitles for lecture sessions.

Reads a session folder from `Audios/<Lecturer>/<Course>/<NNN>/`, aligns the
corrected transcript to the word-level ASR timestamps, and writes the cue
files the player consumes.

Usage:
    python3 align_subtitles.py Audios/Bayat/marefat_nafs/001
    python3 align_subtitles.py --course Audios/Bayat/marefat_nafs
    python3 align_subtitles.py --course Audios/Bayat/marefat_nafs --report-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from align import align_tokens                      # noqa: E402
from cues import build_cues                         # noqa: E402
from transcript import (                            # noqa: E402
    SPOKEN_KINDS,
    parse_cleaned,
    parse_corrected,
    parse_segments,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "website" / "apps" / "web" / "public" / "data"

# A cue boundary can only drift as far as the nearest exact anchor. Isolated
# loose spots are normal (the editor restores book quotations the ASR garbled),
# so the useful signal is how much of the lecture they add up to.
MAX_DRIFT_FRACTION = 0.05


class SessionFiles:
    """Locates the artefacts inside one numbered session folder."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.session_id = folder.name
        self.raw: Optional[Path] = None
        self.corrected: Optional[Path] = None
        self.cleaned: Optional[Path] = None
        self.audio: Optional[Path] = None

        source_audio: Optional[Path] = None
        play_audio: Optional[Path] = None
        for path in sorted(folder.iterdir()):
            if path.is_dir() or path.name.startswith("."):
                continue
            name = path.name
            if name.endswith(".corrected.md"):
                self.corrected = path
            elif name.endswith(".cleaned.txt"):
                self.cleaned = path
            elif name.endswith("_play.m4a") or name.endswith(".play.m4a"):
                # Browser-safe remux with an honest duration (see prepare_playback.py).
                play_audio = path
            elif name.endswith(".mp3") or name.endswith(".m4a"):
                source_audio = path
            elif name.endswith(".txt") and not any(
                name.endswith(suffix)
                for suffix in (".cleaned.txt", ".corrected.txt", ".partial.txt")
            ):
                if not name.startswith("transcribe"):
                    self.raw = path
        self.audio = play_audio or source_audio

    @property
    def stem(self) -> str:
        source = self.raw or self.audio or self.corrected
        return source.name.split(".")[0] if source else self.session_id

    def is_alignable(self) -> bool:
        return self.raw is not None and (
            self.corrected is not None or self.cleaned is not None
        )


def align_session(files: SessionFiles) -> Optional[dict]:
    """Align one session. Returns a result dict, or None if not possible."""
    words = parse_segments(files.raw) if files.raw else []
    if not words:
        return None

    if files.corrected:
        blocks = parse_corrected(files.corrected)
        source = "corrected"
    elif files.cleaned:
        blocks = parse_cleaned(files.cleaned)
        source = "cleaned"
    else:
        return None

    # Align every spoken token in one pass so the diff can use the whole
    # document as context, then hand each block its slice back.
    spoken = [(i, b) for i, b in enumerate(blocks) if b.kind in SPOKEN_KINDS]
    flat_tokens = []
    spans = []
    for block_index, block in spoken:
        start = len(flat_tokens)
        flat_tokens.extend(block.tokens)
        spans.append((block_index, start, len(flat_tokens)))

    if not flat_tokens:
        return None

    timed, stats = align_tokens(words, flat_tokens)
    timed_by_block = {
        block_index: timed[start:end] for block_index, start, end in spans
    }

    cue_list, chapter_list = build_cues(blocks, timed_by_block)

    return {
        "source": source,
        "words": words,
        "blocks": blocks,
        "cues": cue_list,
        "chapters": chapter_list,
        "stats": stats,
        "duration": words[-1].end if words else 0.0,
    }


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis == 1000:
        millis = 999
    return "%02d:%02d:%02d.%03d" % (hours, minutes, secs, millis)


def write_vtt(path: Path, cue_list) -> None:
    lines = ["WEBVTT", ""]
    for cue in cue_list:
        lines.append(str(cue.index + 1))
        lines.append(
            "%s --> %s" % (format_timestamp(cue.start), format_timestamp(cue.end))
        )
        lines.append(cue.text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_cues_json(path: Path, result: dict, session_id: str) -> None:
    payload = {
        "version": 1,
        "sessionId": session_id,
        "lang": "fa",
        "source": result["source"],
        "duration": round(result["duration"], 3),
        "alignment": {
            "exact": result["stats"].exact,
            "total": result["stats"].total,
            "ratio": round(result["stats"].ratio, 4),
            "maxGapSeconds": round(result["stats"].max_gap, 2),
            "p95GapSeconds": round(result["stats"].p95_gap, 2),
            "driftFraction": round(result["stats"].drift_fraction, 4),
        },
        "chapters": [
            {
                "index": c.index,
                "title": c.title,
                "start": round(c.start, 3),
                "end": round(c.end, 3),
            }
            for c in result["chapters"]
        ],
        "cues": [
            {
                "i": c.index,
                "start": round(c.start, 3),
                "end": round(c.end, 3),
                "text": c.text,
                "kind": c.kind,
                "chapter": c.chapter,
                "block": c.block,
                **({"translation": c.translation} if c.translation else {}),
            }
            for c in result["cues"]
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def write_words_json(path: Path, result: dict) -> None:
    """Compact word timings for karaoke-style highlighting."""
    payload = {
        "version": 1,
        "cues": [
            [[round(s, 2), round(e, 2), text] for s, e, text in cue.words]
            for cue in result["cues"]
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def process(files: SessionFiles, out_dir: Path, write: bool) -> dict:
    report = {
        "session": files.session_id,
        "status": "ok",
        "ratio": 0.0,
        "maxGap": 0.0,
        "p95Gap": 0.0,
        "drift": 0.0,
        "cues": 0,
        "chapters": 0,
        "duration": 0.0,
        "source": None,
    }

    if not files.is_alignable():
        report["status"] = "missing-transcript"
        return report

    result = align_session(files)
    if result is None:
        report["status"] = "no-timestamps"
        return report

    report.update(
        ratio=result["stats"].ratio,
        maxGap=result["stats"].max_gap,
        p95Gap=result["stats"].p95_gap,
        drift=result["stats"].drift_fraction,
        cues=len(result["cues"]),
        chapters=len(result["chapters"]),
        duration=result["duration"],
        source=result["source"],
    )
    if result["stats"].drift_fraction > MAX_DRIFT_FRACTION:
        report["status"] = "review"

    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        write_vtt(out_dir / ("%s.vtt" % files.session_id), result["cues"])
        write_cues_json(
            out_dir / ("%s.cues.json" % files.session_id), result, files.session_id
        )
        write_words_json(out_dir / ("%s.words.json" % files.session_id), result)

    return report


def find_sessions(course_dir: Path) -> List[SessionFiles]:
    sessions = []
    for child in sorted(course_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            sessions.append(SessionFiles(child))
    return sessions


def format_duration(seconds: float) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return "%d:%02d:%02d" % (hours, minutes, secs)
    return "%d:%02d" % (minutes, secs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", nargs="?", help="A single session folder")
    parser.add_argument("--course", help="A course folder; processes every session")
    parser.add_argument("--out", default=None, help="Output root (default: public/data)")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Measure alignment quality without writing any files",
    )
    args = parser.parse_args()

    if not args.session and not args.course:
        parser.error("give a session folder or --course")

    if args.course:
        course_dir = Path(args.course).expanduser().resolve()
        sessions = find_sessions(course_dir)
    else:
        session_dir = Path(args.session).expanduser().resolve()
        course_dir = session_dir.parent
        sessions = [SessionFiles(session_dir)]

    lecturer_slug = course_dir.parent.name.lower()
    course_slug = course_dir.name.lower()
    out_root = Path(args.out).expanduser() if args.out else DEFAULT_OUT
    out_dir = out_root / lecturer_slug / course_slug

    print("Course : %s / %s" % (lecturer_slug, course_slug))
    print("Output : %s" % ("(report only)" if args.report_only else out_dir))
    print("")
    header = "%-6s %-10s %8s %8s %8s %7s %6s %6s %9s  %s" % (
        "id", "source", "verbatim", "p95 gap", "max gap", "drift",
        "cues", "chaps", "duration", "status"
    )
    print(header)
    print("-" * len(header))

    reports = []
    for files in sessions:
        report = process(files, out_dir, write=not args.report_only)
        reports.append(report)
        if report["source"] is None:
            continue
        print(
            "%-6s %-10s %7.1f%% %7.1fs %7.1fs %6.1f%% %6d %6d %9s  %s"
            % (
                report["session"],
                report["source"],
                report["ratio"] * 100,
                report["p95Gap"],
                report["maxGap"],
                report["drift"] * 100,
                report["cues"],
                report["chapters"],
                format_duration(report["duration"]),
                report["status"],
            )
        )

    aligned = [r for r in reports if r["status"] in ("ok", "review")]
    skipped = [r for r in reports if r["status"] == "missing-transcript"]
    needs_review = [r for r in reports if r["status"] == "review"]
    print("")
    print(
        "%d of %d sessions aligned (%d still awaiting transcription)"
        % (len(aligned), len(reports), len(skipped))
    )
    if aligned:
        mean_ratio = sum(r["ratio"] for r in aligned) / len(aligned)
        worst_gap = max(r["maxGap"] for r in aligned)
        mean_p95 = sum(r["p95Gap"] for r in aligned) / len(aligned)
        mean_drift = sum(r["drift"] for r in aligned) / len(aligned)
        print("verbatim word match    : %.1f%% mean" % (mean_ratio * 100))
        print("anchor gap             : %.1fs mean p95, %.1fs worst" % (mean_p95, worst_gap))
        print("well-timed audio       : %.1f%% mean" % ((1 - mean_drift) * 100))
        print("total cues             : %d" % sum(r["cues"] for r in aligned))
        print("total chapters         : %d" % sum(r["chapters"] for r in aligned))
    if needs_review:
        print(
            "needs review (>%d%% drift): %s"
            % (MAX_DRIFT_FRACTION * 100, ", ".join(r["session"] for r in needs_review))
        )

    if not args.report_only and aligned:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "_alignment-report.json").write_text(
            json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
