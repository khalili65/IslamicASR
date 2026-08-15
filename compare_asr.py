#!/usr/bin/env python3
"""Run several ASR providers over the same audio and compare the results.

Examples:
    # What is available and which keys are set?
    python compare_asr.py --list

    # Cheap 5-minute bake-off across every provider you have a key for
    python compare_asr.py "Audios/.../lecture.mp3" --providers configured

    # Compare two specific providers on the first 10 minutes
    python compare_asr.py lecture.mp3 -p elevenlabs,fish --sample-minutes 10

    # Full lecture with the winner
    python compare_asr.py lecture.mp3 -p elevenlabs --full
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List

from asr import load_dotenv
from asr.audio import format_hms
from asr.providers import REGISTRY, get_provider
from asr.runner import RunResult, transcribe_file, write_transcript


def key_is_set(cls) -> bool:
    if not cls.env_var:
        return True
    if not os.environ.get(cls.env_var):
        return False
    return all(os.environ.get(name) for name in cls.extra_env)


def print_catalog() -> None:
    print(f"\n{'provider':<15} {'farsi':<14} {'$/audio hr':>11}  {'key':<9} model")
    print("-" * 92)
    for name in sorted(REGISTRY):
        cls = REGISTRY[name]
        price = "free" if cls.price_per_hour_usd == 0 else (
            f"${cls.price_per_hour_usd:.3f}" if cls.price_per_hour_usd is not None else "varies")
        status = "SET" if key_is_set(cls) else "missing"
        print(f"{name:<15} {cls.farsi_support:<14} {price:>11}  {status:<9} {cls.default_model}")

    print("\nEnvironment variables and signup pages:")
    for name in sorted(REGISTRY):
        cls = REGISTRY[name]
        if not cls.env_var:
            print(f"  {name:<15} (no key needed)  {cls.signup_url}")
            continue
        needed = ", ".join([cls.env_var] + list(cls.extra_env))
        print(f"  {name:<15} {needed:<45} {cls.signup_url}")

    print("\nNotes:")
    for name in sorted(REGISTRY):
        cls = REGISTRY[name]
        if cls.notes:
            print(f"  {name}: {cls.notes}")
    print()


def resolve_providers(spec: str) -> List[str]:
    if spec == "all":
        return sorted(REGISTRY)
    if spec == "configured":
        chosen = [n for n in sorted(REGISTRY) if key_is_set(REGISTRY[n])]
        # Local Whisper needs an extra install, so don't opt people in silently.
        return [n for n in chosen if n != "local-whisper"]
    names = [part.strip() for part in spec.split(",") if part.strip()]
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        sys.exit(f"Unknown provider(s): {', '.join(unknown)}\n"
                 f"Available: {', '.join(sorted(REGISTRY))}")
    return names


def write_report(results: List[RunResult], out_dir: Path, media: Path,
                 sample_note: str) -> Path:
    lines = [
        f"# ASR comparison — {media.name}",
        "",
        f"Scope: {sample_note}",
        "",
        "| provider | model | status | chars | segments | time | est. cost |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in results:
        status = "ok" if r.ok else "FAILED"
        cost = "—" if r.cost_usd is None else f"${r.cost_usd:.4f}"
        lines.append(
            f"| {r.provider} | {r.model} | {status} | {len(r.text)} | "
            f"{len(r.segments)} | {r.elapsed_s:.0f}s | {cost} |"
        )

    for r in results:
        lines += ["", f"## {r.label} (`{r.provider}`)", ""]
        if not r.ok:
            lines += [f"**Failed:** {r.error}", ""]
            continue
        preview = r.text[:1500]
        lines += ["```text", preview or "(empty)", "```", ""]

    path = out_dir / "comparison.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare ASR providers on the same audio file.")
    parser.add_argument("input", nargs="?", help="Audio or video file")
    parser.add_argument("-p", "--providers", default="configured",
                        help="Comma-separated names, or 'all' / 'configured' "
                             "(default: configured)")
    parser.add_argument("-l", "--language", default="fa",
                        help="Language code (default: fa)")
    parser.add_argument("--sample-minutes", type=float, default=5.0,
                        help="Only transcribe the first N minutes (default: 5)")
    parser.add_argument("--full", action="store_true",
                        help="Transcribe the whole file instead of a sample")
    parser.add_argument("-o", "--out", default=None,
                        help="Output directory (default: <input>_asr_compare)")
    parser.add_argument("--save-as", default=None,
                        help="Also write the transcript to this exact path. "
                             "Use with a single provider to produce the "
                             "'lecture.txt next to the media' layout that "
                             "prompts/lecture-transcript-pipeline.md expects.")
    parser.add_argument("--model", default=None,
                        help="Override the model for every selected provider")
    parser.add_argument("--diarize", action="store_true",
                        help="Ask for speaker labels where supported")
    parser.add_argument("--price-per-hour", type=float, default=None,
                        help="Override the USD/audio-hour rate used for cost "
                             "estimates (useful when your plan differs)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Ignore and do not write the chunk cache")
    parser.add_argument("--list", action="store_true",
                        help="List providers, prices and key status, then exit")
    args = parser.parse_args()

    load_dotenv()

    if args.list:
        print_catalog()
        return
    if not args.input:
        parser.error("an input file is required (or use --list)")

    media = Path(args.input).expanduser()
    if not media.is_file():
        sys.exit(f"Input file not found: {media}")

    names = resolve_providers(args.providers)
    if not names:
        sys.exit("No providers selected. Add API keys to .env, or use "
                 "`--providers <name>`. Run --list to see what is available.")
    if args.save_as and len(names) > 1:
        sys.exit("--save-as writes a single file, so select exactly one "
                 f"provider (got: {', '.join(names)}).")

    out_dir = Path(args.out).expanduser() if args.out else \
        media.parent / f"{media.stem}_asr_compare"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = None if args.no_cache else out_dir / ".cache"

    max_seconds = None if args.full else args.sample_minutes * 60
    sample_note = ("full file" if args.full
                   else f"first {args.sample_minutes:g} minutes")

    print(f"Input   : {media}")
    print(f"Scope   : {sample_note}")
    print(f"Output  : {out_dir}")
    print(f"Testing : {', '.join(names)}\n")

    results: List[RunResult] = []
    for name in names:
        print(f"[{name}]")
        try:
            provider = get_provider(name, model=args.model, language=args.language,
                                    diarize=args.diarize,
                                    price_per_hour=args.price_per_hour)
        except Exception as exc:  # noqa: BLE001
            print(f"  skipped: {exc}\n")
            continue

        result = transcribe_file(provider, media, cache_dir=cache_dir,
                                 max_seconds=max_seconds,
                                 log=lambda m: print(m, flush=True))
        results.append(result)

        if result.ok:
            out_file = out_dir / f"{media.stem}.{name}.txt"
            write_transcript(result, out_file)
            cost = "—" if result.cost_usd is None else f"${result.cost_usd:.4f}"
            print(f"  done: {len(result.text)} chars, {len(result.segments)} segments, "
                  f"{result.elapsed_s:.0f}s, est. {cost}")
            print(f"  saved: {out_file}")
            if args.save_as:
                canonical = Path(args.save_as).expanduser()
                write_transcript(result, canonical)
                print(f"  saved: {canonical}")
            print()
        else:
            print(f"  FAILED: {result.error}\n")

    if not results:
        sys.exit("Nothing ran.")

    report = write_report(results, out_dir, media, sample_note)

    print("=" * 78)
    print(f"{'provider':<15} {'chars':>7} {'segs':>6} {'time':>7} {'est. cost':>10}  status")
    print("-" * 78)
    for r in results:
        cost = "—" if r.cost_usd is None else f"${r.cost_usd:.4f}"
        print(f"{r.provider:<15} {len(r.text):>7} {len(r.segments):>6} "
              f"{r.elapsed_s:>6.0f}s {cost:>10}  {'ok' if r.ok else 'FAILED'}")
    print("=" * 78)

    ok = [r for r in results if r.ok]
    if ok:
        print(f"Audio scope: {format_hms(ok[0].duration)}")
    print(f"Report: {report}")
    print("\nRead the transcripts side by side and judge Persian quality yourself — "
          "character count is not accuracy.")


if __name__ == "__main__":
    main()
