#!/usr/bin/env python3
"""Move legacy / old-pipeline files out of session folders; keep raw ASR only.

For each numbered folder under a course, copies non-raw artefacts into
`_legacy/<NNN>/` beside the session (same course root). The session folder
then holds only raw `*.txt`, audio, and optional fresh `*.book.md` /
`*.summary.md` from the new pipeline.

Usage:
    python scripts/reorg_pipeline_sessions.py Audios/Bayat/marefat_nafs --start 1 --end 10
    python scripts/reorg_pipeline_sessions.py Audios/Bayat/marefat_nafs --start 1 --end 10 --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RAW_TXT_SKIP = (".cleaned.txt", ".corrected.txt", ".partial.txt", ".rawbak")
KEEP_SUFFIXES = (
    ".book.md",
    ".summary.md",
)
MOVE_SUFFIXES = (
    ".corrected.md",
    ".cleaned.txt",
    ".corrected.txt",
    ".book.prev.md",
    ".summary.prev.md",
)
MOVE_PREFIXES = (
    "pipeline_",
    ".book_parts_",
    ".summary_parts_",
)


def is_raw_txt(path: Path) -> bool:
    name = path.name
    if not name.endswith(".txt"):
        return False
    return not any(name.endswith(s) for s in RAW_TXT_SKIP)


def should_move(path: Path, keep_pipeline: bool) -> bool:
    name = path.name
    if path.is_dir():
        return any(name.startswith(p) for p in MOVE_PREFIXES)
    if keep_pipeline and any(name.endswith(s) for s in KEEP_SUFFIXES):
        return False
    if any(name.endswith(s) for s in MOVE_SUFFIXES):
        return True
    if name.startswith("pipeline_"):
        return True
    if name.endswith(".book.md") or name.endswith(".summary.md"):
        return True
    return False


def reorg_session(session_dir: Path, legacy_root: Path, dry_run: bool, keep_pipeline: bool) -> list[str]:
    actions: list[str] = []
    legacy_dir = legacy_root / session_dir.name
    for path in sorted(session_dir.iterdir()):
        if path.name in (".", ".."):
            continue
        if path.is_file() and is_raw_txt(path):
            continue
        if path.suffix in (".mp3", ".m4a") or path.name.endswith("_play.m4a"):
            continue
        if path.is_dir() and not any(path.name.startswith(p) for p in MOVE_PREFIXES):
            continue
        if path.is_file() and path.name.startswith(".") and not path.name.startswith(".book_parts_") and not path.name.startswith(".summary_parts_"):
            continue
        if not should_move(path, keep_pipeline):
            continue
        dest = legacy_dir / path.name
        actions.append(f"move {path.relative_to(session_dir.parent.parent)} -> _legacy/{session_dir.name}/{path.name}")
        if not dry_run:
            legacy_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if path.is_dir():
                    dest = legacy_dir / f"{path.name}.dup"
                else:
                    stem = path.stem
                    suffix = "".join(path.suffixes) or path.suffix
                    n = 2
                    while dest.exists():
                        dest = legacy_dir / f"{stem}.dup{n}{suffix}"
                        n += 1
            if path.is_dir():
                shutil.move(str(path), str(dest))
            else:
                shutil.move(str(path), str(dest))
    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course", type=Path, help="Course folder, e.g. Audios/Bayat/marefat_nafs")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument(
        "--keep-pipeline",
        action="store_true",
        help="Leave existing *.book.md and *.summary.md in the session folder (e.g. session 001).",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    course = args.course.expanduser().resolve()
    if not course.is_dir():
        sys.exit(f"Not a directory: {course}")

    legacy_root = course / "_legacy"
    all_actions: list[str] = []
    for n in range(args.start, args.end + 1):
        session = course / f"{n:03d}"
        if not session.is_dir():
            print(f"skip {session.name}: missing")
            continue
        keep = args.keep_pipeline and n == args.start
        all_actions.extend(reorg_session(session, legacy_root, args.dry_run, keep))

    if not all_actions:
        print("Nothing to move.")
        return
    for line in all_actions:
        print(line)
    print(f"\n{'Would move' if args.dry_run else 'Moved'} {len(all_actions)} file(s) into {legacy_root}/")


if __name__ == "__main__":
    main()
