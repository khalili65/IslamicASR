"""Build a browser-safe playback copy of each lecture mp3.

Many of the source mp3s advertise a container duration a few seconds shorter
than the number of samples they actually contain. Chrome's HTMLMediaElement
then reports the short duration; seeking on the progress bar lands on the
wrong audio, which feels like growing subtitle lag the further you jump.

We leave the originals untouched and write `<stem>.play.m4a` next to them —
AAC in an MP4 container whose duration matches the decoded length.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asr.audio import ffmpeg_paths, probe_duration  # noqa: E402


PLAY_NAME = "%s_play.m4a"  # ASCII-only; Persian stems break some ffmpeg temp paths
# Remux when the container under-reports by more than this.
MISMATCH_THRESHOLD_S = 0.4


def decoded_duration(path: Path) -> float:
    """Count samples by decoding — ground truth for HTML5 playback length."""
    ff, _ = ffmpeg_paths()
    result = subprocess.run(
        [ff, "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    import re

    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", result.stderr)
    if not times:
        raise RuntimeError("could not decode duration for %s" % path)
    h, m, s = times[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def play_path_for(src: Path) -> Path:
    """`Audios/.../001/foo.mp3` → `Audios/.../001/001_play.m4a`."""
    return src.parent / (PLAY_NAME % src.parent.name)


def needs_rebuild(src: Path, dest: Path) -> bool:
    if not dest.exists():
        return True
    return dest.stat().st_mtime < src.stat().st_mtime


def build_play_file(src: Path, dest: Path) -> float:
    ff, _ = ffmpeg_paths()
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Write to a short ASCII temp name in /tmp, then move — avoids ffmpeg
    # choking on long Persian paths when doing the faststart second pass.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "play.m4a"
        proc = subprocess.run(
            [
                ff,
                "-y",
                "-i",
                str(src),
                "-map_metadata",
                "-1",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(tmp_out),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "ffmpeg failed for %s:\n%s" % (src.name, proc.stderr[-800:])
            )
        dest.write_bytes(tmp_out.read_bytes())
    return probe_duration(dest) or 0.0


def prepare_session_audio(src: Path, *, force: bool = False) -> Path:
    """Return the file the web player should use for `src`."""
    container = probe_duration(src) or 0.0
    true = decoded_duration(src)
    dest = play_path_for(src)

    if abs(true - container) < MISMATCH_THRESHOLD_S and not force:
        # Container is honest — keep serving the original.
        if dest.exists():
            dest.unlink()
        return src

    if force or needs_rebuild(src, dest):
        built = build_play_file(src, dest)
        print(
            "  %s  container=%.2fs  decoded=%.2fs  → %s (%.2fs)"
            % (src.name, container, true, dest.name, built)
        )
    else:
        print("  %s  reuse %s" % (src.name, dest.name))
    return dest


def iter_session_mp3s(course_dir: Path):
    for child in sorted(course_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        for audio in sorted(child.iterdir()):
            if audio.suffix.lower() == ".mp3" and not audio.name.endswith(".play.mp3"):
                yield audio


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--course",
        type=Path,
        required=True,
        help="Audios/<Lecturer>/<Course> directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild .play.m4a even when the source is unchanged",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process the first N sessions (0 = all)",
    )
    args = parser.parse_args()
    course = args.course.resolve()
    if not course.is_dir():
        print("not a directory: %s" % course, file=sys.stderr)
        return 1

    count = 0
    for src in iter_session_mp3s(course):
        prepare_session_audio(src, force=args.force)
        count += 1
        if args.limit and count >= args.limit:
            break
    print("done: %d file(s)" % count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
