"""Runs a Provider over a (possibly long) media file with caching."""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from . import audio as audio_utils
from .providers import ChunkResult, Provider, ProviderError, Segment


@dataclass
class RunResult:
    provider: str
    label: str
    model: str
    text: str = ""
    segments: List[Segment] = field(default_factory=list)
    duration: float = 0.0
    chunks: int = 0
    elapsed_s: float = 0.0
    cost_usd: Optional[float] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _cache_key(provider: Provider, media: Path, start: float, dur: float) -> str:
    raw = f"{provider.name}|{provider.model}|{provider.language}|{media.name}|{start:.2f}|{dur:.2f}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def write_partial_transcript(
    path: Path,
    texts: List[str],
    segments: List[Segment],
    *,
    covered_until: float,
    total_duration: float,
    with_segments: bool = True,
) -> None:
    """Overwrite a progress file after each finished chunk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# partial — covered {audio_utils.format_hms(covered_until)} / "
        f"{audio_utils.format_hms(total_duration)}\n\n"
    )
    body = "\n".join(t for t in texts if t).strip()
    lines = [header + body, ""]
    if with_segments and segments:
        lines.append("--- Segments ---")
        for seg in segments:
            speaker = f" <{seg.speaker}>" if seg.speaker else ""
            lines.append(
                f"[{seg.start:>8.2f}s - {seg.end:>8.2f}s]{speaker} {seg.text}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def transcribe_file(
    provider: Provider,
    media_path: Path,
    *,
    cache_dir: Optional[Path] = None,
    max_seconds: Optional[float] = None,
    chunk_seconds: Optional[float] = None,
    progress_path: Optional[Path] = None,
    with_segments: bool = True,
    log: Callable[[str], None] = print,
) -> RunResult:
    """Transcribe `media_path` with `provider`, chunking when the API requires it.

    `max_seconds` transcribes only the first N seconds (cheap smoke test).
    `chunk_seconds` forces smaller requests even when the provider allows big
    uploads — useful with ElevenLabs so each finished piece is cached and written
    to `progress_path` before the whole lecture is done.
    """
    started = time.time()
    result = RunResult(provider=provider.name, label=provider.label,
                       model=provider.model)

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / "source.mp3"
            log(f"  preparing audio ({media_path.name})...")
            audio_utils.to_speech_mp3(media_path, source)

            duration = audio_utils.probe_duration(source) or 0.0
            if max_seconds:
                duration = min(duration, max_seconds)
            result.duration = duration

            chunk_len = provider.max_chunk_seconds or duration
            if chunk_seconds and chunk_seconds > 0:
                chunk_len = min(chunk_len, chunk_seconds) if chunk_len else chunk_seconds
            # Respect an upload-size cap by shortening chunks if needed.
            if provider.max_upload_bytes:
                bytes_per_second = source.stat().st_size / max(
                    audio_utils.probe_duration(source) or 1.0, 1.0)
                affordable = provider.max_upload_bytes * 0.9 / max(bytes_per_second, 1.0)
                chunk_len = min(chunk_len or affordable, affordable)

            chunks = audio_utils.plan_chunks(duration, chunk_len)
            result.chunks = len(chunks)
            log(f"  {audio_utils.format_hms(duration)} → {len(chunks)} request(s)")
            if progress_path:
                log(f"  progress file: {progress_path}")

            texts: List[str] = []
            for index, (start, dur) in enumerate(chunks, start=1):
                cached = None
                cache_path = None
                if cache_dir:
                    cache_path = cache_dir / f"{_cache_key(provider, media_path, start, dur)}.json"
                    if cache_path.exists():
                        cached = json.loads(cache_path.read_text(encoding="utf-8"))

                if cached is not None:
                    log(f"  [{index}/{len(chunks)}] cached")
                    chunk = ChunkResult(
                        text=cached.get("text", ""),
                        segments=[Segment(**s) for s in cached.get("segments", [])],
                    )
                else:
                    piece = tmpdir / f"chunk_{index:03d}.mp3"
                    if len(chunks) == 1 and start == 0.0 and not max_seconds:
                        piece = source
                    else:
                        audio_utils.export_chunk(source, piece, start, dur)
                    log(f"  [{index}/{len(chunks)}] "
                        f"{audio_utils.format_hms(start)}–{audio_utils.format_hms(start + dur)} "
                        f"({piece.stat().st_size / 1024:.0f} KB)...")
                    chunk = provider.transcribe_chunk(piece)
                    if cache_path:
                        cache_path.write_text(json.dumps({
                            "text": chunk.text,
                            "segments": [vars(s) for s in chunk.segments],
                        }, ensure_ascii=False), encoding="utf-8")

                if chunk.text:
                    texts.append(chunk.text)
                    preview = chunk.text.strip().replace("\n", " ")
                    if len(preview) > 180:
                        preview = preview[:180] + "…"
                    log(f"      → {len(chunk.text)} chars: {preview}")
                for seg in chunk.segments:
                    result.segments.append(Segment(seg.start + start, seg.end + start,
                                                   seg.text, seg.speaker))

                if progress_path:
                    write_partial_transcript(
                        progress_path, texts, result.segments,
                        covered_until=start + dur,
                        total_duration=duration,
                        with_segments=with_segments,
                    )

            result.text = "\n".join(texts).strip()
    except (ProviderError, audio_utils.FfmpegMissing) as exc:
        result.error = str(exc)
    except Exception as exc:  # noqa: BLE001
        result.error = f"{type(exc).__name__}: {exc}"

    result.elapsed_s = time.time() - started
    result.cost_usd = provider.estimate_cost(result.duration)
    return result


def write_transcript(result: RunResult, path: Path, *, with_segments: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [result.text.strip(), ""]
    if with_segments and result.segments:
        lines.append("--- Segments ---")
        for seg in result.segments:
            speaker = f" <{seg.speaker}>" if seg.speaker else ""
            lines.append(
                f"[{seg.start:>8.2f}s - {seg.end:>8.2f}s]{speaker} {seg.text}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
