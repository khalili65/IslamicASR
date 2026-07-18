#!/usr/bin/env python3
"""Resume-capable Fish ASR with cache + 503 subdivide. Usage:
  python scripts/asr_resume.py PATH_TO_MP4 [--cache-name NAME]
"""
from __future__ import annotations
import argparse, json, math, os, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from transcribe import (
    load_dotenv, prepare_source_audio, probe_duration_seconds, plan_chunks,
    export_chunk, format_hms, merge_chunk_results, PRICE_PER_SECOND_USD,
    transcribe_bytes,
)
load_dotenv(ROOT / ".env")
from fishaudio import FishAudio


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--cache-name", default=None)
    ap.add_argument("--language", default="fa")
    args = ap.parse_args()

    mp4 = Path(args.input).expanduser().resolve()
    if not mp4.is_file():
        sys.exit(f"not found: {mp4}")

    cache_dir = mp4.parent / (args.cache_name or f".asr_cache_{mp4.stem[:40]}")
    cache_dir.mkdir(exist_ok=True)
    client = FishAudio(api_key=os.environ["FISH_API_KEY"])
    print(f"FILE: {mp4.name}", flush=True)
    print(f"CACHE: {cache_dir}", flush=True)

    def transcribe_range(source, start, dur, tag):
        cache_path = cache_dir / f"{tag}.json"
        if cache_path.exists():
            data = json.loads(cache_path.read_text())
            print(f"  CACHE {tag} text_len={len(data.get('text',''))}", flush=True)
            return data

        with tempfile.TemporaryDirectory() as tmp:
            chunk_path = Path(tmp) / f"{tag}.mp3"
            export_chunk(source, chunk_path, start, dur)
            size_kb = chunk_path.stat().st_size // 1024
            print(f"  try {format_hms(start)}–{format_hms(start+dur)} ({size_kb}KB)", flush=True)
            try:
                audio = chunk_path.read_bytes()
                r = transcribe_bytes(client, audio, language=args.language, include_timestamps=True)
                text = getattr(r, "text", None) or ""
                segs = []
                for s in (getattr(r, "segments", None) or []):
                    segs.append({
                        "text": getattr(s, "text", "") or "",
                        "start": float(getattr(s, "start", 0) or 0),
                        "end": float(getattr(s, "end", 0) or 0),
                    })
                data = {"offset": start, "duration": dur, "text": text, "segments": segs}
                cache_path.write_text(json.dumps(data, ensure_ascii=False))
                print(f"    OK text_len={len(text)}", flush=True)
                return data
            except Exception as e:
                print(f"    FAIL: {e}", flush=True)
                if dur <= 25:
                    raise
                step = 60 if dur > 60 else 20
                pieces = []
                t = start
                end = start + dur
                while t < end:
                    d = min(step, end - t)
                    subtag = f"{tag}_s{int(t)}_{int(d)}"
                    pieces.append(transcribe_range(source, t, d, subtag))
                    t += d
                texts = [p["text"] for p in pieces if p.get("text")]
                segs_out = []
                for p in pieces:
                    off = p["offset"]
                    for s in p.get("segments") or []:
                        segs_out.append({
                            "text": s["text"],
                            "start": (s["start"] + off) - start,
                            "end": (s["end"] + off) - start,
                        })
                data = {"offset": start, "duration": dur, "text": " ".join(texts), "segments": segs_out}
                cache_path.write_text(json.dumps(data, ensure_ascii=False))
                return data

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        print("Converting to audio...", flush=True)
        source = prepare_source_audio(mp4, tmpdir)
        duration = probe_duration_seconds(source)
        chunks = plan_chunks(duration, source.stat().st_size)
        print(f"Total {format_hms(duration)}, {len(chunks)} chunks", flush=True)

        results = []
        for i, (start, dur) in enumerate(chunks, 1):
            print(f"[{i}/{len(chunks)}]", flush=True)
            tag = f"c{i:02d}_{int(start)}_{int(dur)}"
            results.append(transcribe_range(source, start, dur, tag))

        class Seg:
            def __init__(self, text, start, end):
                self.text, self.start, self.end = text, start, end

        class Res:
            def __init__(self, text, segments, duration=0):
                self.text, self.segments, self.duration = text, segments, duration

        api_results = []
        for d in results:
            segs = [Seg(s["text"], s["start"], s["end"]) for s in d.get("segments") or []]
            api_results.append((d["offset"], Res(d.get("text") or "", segs, d.get("duration") or 0)))

        merged = merge_chunk_results(api_results)
        out = mp4.with_suffix(".txt")
        lines = [merged.text.strip(), "", "--- Segments ---"]
        for s in merged.segments:
            lines.append(f"[{format_hms(s.start)} → {format_hms(s.end)}] {s.text}")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        cost = math.ceil(duration) * PRICE_PER_SECOND_USD
        print("=" * 60)
        print(f"Saved: {out}")
        print(f"Duration: {format_hms(duration)}  cost≈ ${cost:.4f}")
        print(f"chars={len(merged.text)} segs={len(merged.segments)}")
        print("Preview:")
        print(merged.text[:600])


if __name__ == "__main__":
    main()
