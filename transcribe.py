#!/usr/bin/env python3
"""Transcribe any audio/video file and report the cost.

Usage:
    python transcribe.py path/to/file.mp4
    python transcribe.py path/to/file.mp3 --language fa
    python transcribe.py path/to/file.mp3 --provider elevenlabs --language fa
    python transcribe.py path/to/file.wav --output my_transcript.txt

Two providers are available: `fish` (default) and `elevenlabs`. Long files are
split into chunks automatically when the provider requires it — Fish caps a
request at 20 MB / 60 min and its word timestamps stop advancing after ~4 min,
while ElevenLabs takes the whole lecture in one request.

The API key is read from FISH_API_KEY or ELEVENLABS_API_KEY (a local .env file
is loaded automatically if present).
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Fish Audio ASR pricing: $0.36 per audio hour, billed on the duration
# processed and rounded up to the nearest second.
PRICE_PER_HOUR_USD = 0.36
PRICE_PER_SECOND_USD = PRICE_PER_HOUR_USD / 3600.0

# Fish Audio ASR limits:
# 1) Decoded PCM must stay under ~20 MB (~10.9 min at 16 kHz mono 16-bit).
# 2) Word-level timestamps stop updating after ~4 minutes even when the
#    returned text covers the whole chunk — empirically ts_max freezes
#    around ~239s. Keep chunks at 3 minutes so timestamps stay complete.
MAX_CHUNK_SECONDS = 3 * 60
CHUNK_BITRATE = "48k"

AUDIO_EXTS_DIRECT = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".aac"}


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    text: str
    duration: float
    segments: list[Segment]


def load_dotenv(path: Path) -> None:
    """Minimal .env loader so we don't require python-dotenv."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def resolve_ffmpeg() -> tuple[str, str]:
    """Locate ffmpeg/ffprobe, including the pip-installed static binaries."""
    from asr.audio import ffmpeg_paths

    return ffmpeg_paths()


def have_ffmpeg() -> bool:
    try:
        resolve_ffmpeg()
        return True
    except Exception:  # noqa: BLE001
        return False


def probe_duration_seconds(path: Path) -> float | None:
    try:
        _, ffprobe = resolve_ffmpeg()
    except Exception:  # noqa: BLE001
        return None
    try:
        out = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(out.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def extract_audio(src: Path, dst: Path) -> None:
    """Extract/transcode the audio track to mono speech-friendly mp3."""
    ffmpeg, _ = resolve_ffmpeg()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            CHUNK_BITRATE,
            str(dst),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def export_chunk(src: Path, dst: Path, start: float, duration: float) -> None:
    ffmpeg, _ = resolve_ffmpeg()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            CHUNK_BITRATE,
            str(dst),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def prepare_source_audio(input_path: Path, tmpdir: Path) -> Path:
    """Return a path to a speech mp3 of the input (converting if needed)."""
    ext = input_path.suffix.lower()
    if ext == ".mp3":
        # Re-encode to known bitrate so chunk sizing is predictable.
        converted = tmpdir / "source.mp3"
        print(f"Preparing audio from '{input_path.name}'...")
        try:
            extract_audio(input_path, converted)
        except subprocess.CalledProcessError as exc:
            sys.exit(f"ffmpeg failed to prepare audio:\n{exc.stderr}")
        return converted

    if ext in AUDIO_EXTS_DIRECT and have_ffmpeg():
        converted = tmpdir / "source.mp3"
        print(f"Converting '{input_path.name}' to audio with ffmpeg...")
        try:
            extract_audio(input_path, converted)
        except subprocess.CalledProcessError as exc:
            sys.exit(f"ffmpeg failed to extract audio:\n{exc.stderr}")
        return converted

    if ext in AUDIO_EXTS_DIRECT:
        return input_path

    if not have_ffmpeg():
        sys.exit(
            f"'{ext}' needs conversion but ffmpeg was not found. "
            "Install it (e.g. `brew install ffmpeg`) or provide an audio file."
        )

    converted = tmpdir / "source.mp3"
    print(f"Converting '{input_path.name}' to audio with ffmpeg...")
    try:
        extract_audio(input_path, converted)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"ffmpeg failed to extract audio:\n{exc.stderr}")
    return converted


def plan_chunks(total_duration: float, file_size_bytes: int) -> list[tuple[float, float]]:
    """Return list of (start, duration) chunks under API PCM/duration limits."""
    del file_size_bytes  # sizing is driven by decoded PCM, not compressed size
    if total_duration <= 0:
        return [(0.0, 0.0)]

    chunk_len = min(MAX_CHUNK_SECONDS, total_duration)
    chunks: list[tuple[float, float]] = []
    start = 0.0
    while start < total_duration - 0.05:
        duration = min(chunk_len, total_duration - start)
        chunks.append((start, duration))
        start += duration
    return chunks


def format_hms(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def normalize_segment_time(value: float) -> float:
    """Fish Audio may return ms or seconds; normalize to seconds."""
    # Heuristic: values >> typical duration are milliseconds.
    if value > 10_000:
        return value / 1000.0
    return value


def transcribe_bytes(
    client,
    audio_bytes: bytes,
    language: str | None,
    include_timestamps: bool,
    *,
    max_attempts: int = 4,
):
    kwargs = {
        "audio": audio_bytes,
        "include_timestamps": include_timestamps,
    }
    if language:
        kwargs["language"] = language

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.asr.transcribe(**kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            msg = str(exc).lower()
            retryable = any(
                token in msg
                for token in ("503", "502", "504", "timeout", "timed out", "temporar")
            )
            if not retryable or attempt == max_attempts:
                raise
            wait = min(2 ** attempt, 20)
            print(
                f"    retry {attempt}/{max_attempts - 1} after error "
                f"({exc}); sleeping {wait}s..."
            )
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def merge_chunk_results(chunk_results: list[tuple[float, object]]) -> TranscriptResult:
    texts: list[str] = []
    segments: list[Segment] = []
    total_duration = 0.0

    for offset, result in chunk_results:
        text = (getattr(result, "text", None) or "").strip()
        if text:
            texts.append(text)

        chunk_duration = float(getattr(result, "duration", 0) or 0)
        # Duration may also be in ms.
        if chunk_duration > 10_000:
            chunk_duration = chunk_duration / 1000.0
        total_duration = max(total_duration, offset + chunk_duration)

        for seg in getattr(result, "segments", None) or []:
            start = normalize_segment_time(float(getattr(seg, "start", 0) or 0))
            end = normalize_segment_time(float(getattr(seg, "end", 0) or 0))
            seg_text = getattr(seg, "text", "") or ""
            segments.append(Segment(start=offset + start, end=offset + end, text=seg_text))

    return TranscriptResult(
        text="\n".join(texts).strip(),
        duration=total_duration,
        segments=segments,
    )


PROVIDERS = ("fish", "elevenlabs")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio/video file and show the cost."
    )
    parser.add_argument("input", help="Path to the audio or video file")
    parser.add_argument(
        "-p",
        "--provider",
        default="fish",
        choices=PROVIDERS,
        help="Which ASR service to use (default: fish).",
    )
    parser.add_argument(
        "-l",
        "--language",
        default=None,
        help="Language code (e.g. en, zh, fa, ar). Auto-detected if omitted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Where to write the transcript. Defaults to <input>.txt",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Override the provider's default model.",
    )
    parser.add_argument(
        "--no-timestamps",
        action="store_true",
        help="Do not include per-segment timestamps in the saved transcript.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not reuse or write the per-chunk cache.",
    )
    parser.add_argument(
        "--max-minutes",
        type=float,
        default=None,
        help="Only transcribe the first N minutes (cheap smoke test).",
    )
    parser.add_argument(
        "--chunk-minutes",
        type=float,
        default=None,
        help="Force N-minute chunks even when the provider allows a larger "
             "upload. Each finished chunk is cached and written to "
             "<output>.partial.txt so you can watch progress.",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).with_name(".env"))

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        sys.exit(f"Input file not found: {input_path}")

    from asr.providers import ProviderError, get_provider
    from asr.runner import transcribe_file

    try:
        provider = get_provider(args.provider, model=args.model,
                                language=args.language)
        provider.require_key()
    except ProviderError as exc:
        sys.exit(str(exc))

    output_path = (
        Path(args.output).expanduser()
        if args.output
        else input_path.with_suffix(".txt")
    )
    progress_path = output_path.with_suffix(".partial.txt")

    cache_dir = None
    if not args.no_cache:
        cache_dir = input_path.parent / f".asr_cache_{input_path.stem[:40]}"

    max_seconds = args.max_minutes * 60 if args.max_minutes else None
    chunk_seconds = args.chunk_minutes * 60 if args.chunk_minutes else None

    print(f"Provider: {provider.label} ({provider.model})")
    if max_seconds:
        print(f"Smoke test: first {args.max_minutes:g} minute(s) only")
    if chunk_seconds:
        print(f"Forced chunks: {args.chunk_minutes:g} minute(s)")
    print(f"Progress file (updated after each chunk): {progress_path}")

    result = transcribe_file(
        provider, input_path,
        cache_dir=cache_dir,
        max_seconds=max_seconds,
        chunk_seconds=chunk_seconds,
        progress_path=progress_path,
        with_segments=not args.no_timestamps,
        log=lambda m: print(m, flush=True),
    )
    if not result.ok:
        sys.exit(f"Transcription failed: {result.error}")

    billed_seconds = math.ceil(result.duration) if result.duration else 0
    cost = result.cost_usd

    with output_path.open("w", encoding="utf-8") as f:
        f.write(result.text.strip() + "\n")
        if result.segments and not args.no_timestamps:
            f.write("\n--- Segments ---\n")
            for seg in result.segments:
                f.write(f"[{seg.start:>8.2f}s - {seg.end:>8.2f}s] {seg.text}\n")

    # Final file is ready; drop the partial marker.
    if progress_path.exists():
        progress_path.unlink()

    preview = result.text.strip()
    if len(preview) > 2000:
        preview = preview[:2000] + "\n… (truncated; see saved file for full transcript)"

    rate = ("n/a" if provider.price_per_hour is None
            else f"${provider.price_per_hour:.2f} / audio hour")

    print("\n" + "=" * 60)
    print("TRANSCRIPTION (preview)")
    print("=" * 60)
    print(preview)
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Input file      : {input_path.name}")
    print(f"Provider        : {provider.label} ({provider.model})")
    print(f"Audio duration  : {format_hms(result.duration)} ({result.duration:.2f} s)")
    print(f"Requests        : {result.chunks}")
    print(f"Billed duration : {billed_seconds} s (rounded up to nearest second)")
    print(f"Rate            : {rate}")
    print(f"Estimated cost  : ${cost:.6f} USD" if cost is not None
          else "Estimated cost  : n/a")
    print(f"Transcript saved: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
