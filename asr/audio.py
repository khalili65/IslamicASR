"""Audio helpers: ffmpeg discovery, probing, transcoding and chunking."""

from __future__ import annotations

import functools
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

# Speech-friendly encoding used for every provider so comparisons are fair.
TARGET_SAMPLE_RATE = 16000
TARGET_BITRATE = "48k"

MEDIA_EXTS = {
    ".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".wma",
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".ts",
}


class FfmpegMissing(RuntimeError):
    pass


@functools.lru_cache(maxsize=1)
def ffmpeg_paths() -> Tuple[str, str]:
    """Locate ffmpeg and ffprobe, falling back to the pip-installed binaries.

    Homebrew is not available on every machine, so `pip install static-ffmpeg`
    is a supported way to provide the binaries.
    """
    env_ffmpeg = os.environ.get("FFMPEG_BINARY")
    env_ffprobe = os.environ.get("FFPROBE_BINARY")
    if env_ffmpeg and env_ffprobe:
        return env_ffmpeg, env_ffprobe

    found = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if all(found):
        return found[0], found[1]  # type: ignore[return-value]

    try:
        from static_ffmpeg import run as static_run

        return static_run.get_or_fetch_platform_executables_else_raise()
    except Exception as exc:  # noqa: BLE001
        raise FfmpegMissing(
            "ffmpeg/ffprobe not found. Install one of:\n"
            "  pip install static-ffmpeg      (no admin rights needed)\n"
            "  brew install ffmpeg            (if you have Homebrew)\n"
            "or set FFMPEG_BINARY and FFPROBE_BINARY."
        ) from exc


def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def probe_duration(path: Path) -> Optional[float]:
    try:
        _, ffprobe = ffmpeg_paths()
    except FfmpegMissing:
        return estimate_mp3_duration(path)
    try:
        out = _run([
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ])
        return float(out.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return estimate_mp3_duration(path)


def estimate_mp3_duration(path: Path) -> Optional[float]:
    """Rough CBR mp3 duration from the first frame header (ffprobe fallback)."""
    if path.suffix.lower() != ".mp3":
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None

    v1l3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    v2l3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
    rates = {3: {0: 44100, 1: 48000, 2: 32000}, 2: {0: 22050, 1: 24000, 2: 16000}}

    i = 0
    if data[:3] == b"ID3" and len(data) > 10:
        # ID3 size is a synchsafe integer: 7 significant bits per byte.
        size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | \
               ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        i = 10 + size

    while i < len(data) - 4:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            version = (data[i + 1] >> 3) & 3
            layer = (data[i + 1] >> 1) & 3
            bitrate_idx = (data[i + 2] >> 4) & 0xF
            rate_idx = (data[i + 2] >> 2) & 3
            if version in (2, 3) and layer == 1 and bitrate_idx not in (0, 15) and rate_idx != 3:
                bitrate = (v1l3 if version == 3 else v2l3)[bitrate_idx] * 1000
                if bitrate:
                    return (len(data) - i) * 8 / bitrate
        i += 1
    return None


def to_speech_mp3(src: Path, dst: Path) -> Path:
    """Transcode any media to mono 16 kHz mp3 (drops video)."""
    ffmpeg, _ = ffmpeg_paths()
    _run([
        ffmpeg, "-y", "-i", str(src),
        "-vn", "-ac", "1", "-ar", str(TARGET_SAMPLE_RATE), "-b:a", TARGET_BITRATE,
        str(dst),
    ])
    return dst


def export_chunk(src: Path, dst: Path, start: float, duration: float) -> Path:
    ffmpeg, _ = ffmpeg_paths()
    _run([
        ffmpeg, "-y",
        "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src),
        "-vn", "-ac", "1", "-ar", str(TARGET_SAMPLE_RATE), "-b:a", TARGET_BITRATE,
        str(dst),
    ])
    return dst


def plan_chunks(total_duration: float, chunk_seconds: float) -> List[Tuple[float, float]]:
    if total_duration <= 0:
        return [(0.0, 0.0)]
    if chunk_seconds <= 0 or chunk_seconds >= total_duration:
        return [(0.0, total_duration)]

    chunks: List[Tuple[float, float]] = []
    start = 0.0
    while start < total_duration - 0.05:
        chunks.append((start, min(chunk_seconds, total_duration - start)))
        start += chunk_seconds
    return chunks


def format_hms(seconds: float) -> str:
    seconds = int(round(seconds or 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"
