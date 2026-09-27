#!/usr/bin/env python3
"""Run the lecture-transcript pipeline through the native Gemini.app.

Same prompts, chunking, part-caching and output layout as gemini_book_style.py
— only the transport differs. The web UI began rejecting every send with Google's
server-side error 1095, so this drives the macOS app over the Accessibility API
instead. Replies are read back with each message's "Copy response" button, which
returns the original Markdown rather than flattened screen text.

Examples:
    python scripts/gemini_app_pipeline.py Audios/Qasemian/InsaneKamel --dry-run
    python scripts/gemini_app_pipeline.py Audios/Qasemian/InsaneKamel
    python scripts/gemini_app_pipeline.py Audios/Qasemian/InsaneKamel --summarize
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gemini_book_style as gb  # noqa: E402
from gemini_mac_app import GeminiApp, log  # noqa: E402


class ChunkFailed(RuntimeError):
    pass


def ask_with_retries(
    app: GeminiApp,
    message: str,
    args,
    fresh: bool,
    chunk: str | None = None,
    must_contain: str = "",
) -> str:
    """Send one message, insisting on a reply that actually looks like our output."""
    last_error = ""
    for attempt in range(1, args.retries + 1):
        try:
            raw = app.ask(message, fresh=fresh or attempt > 1, timeout=args.timeout)
        except RuntimeError as exc:
            last_error = str(exc)
            log(f"    attempt {attempt}/{args.retries} failed: {last_error}")
            time.sleep(args.delay)
            continue

        reply = gb._clean_model_reply(gb._strip_code_fence(raw))
        if not gb._reply_looks_usable(reply, chunk):
            last_error = f"unusable reply ({len(reply)} chars)"
            log(f"    attempt {attempt}/{args.retries}: {last_error}; retrying in a new chat")
            time.sleep(args.delay)
            continue
        if must_contain and must_contain not in message:
            log("    note: anchor missing from the prompt itself")
        return reply

    raise ChunkFailed(last_error or "no usable reply")


def process_transcript(app: GeminiApp, transcript: Path, args) -> Path | None:
    raw = transcript.read_text(encoding="utf-8")
    text = gb.continuous_text(raw)
    chunks = gb.split_chunks(text, args.chunk_chars)
    if not chunks:
        log(f"Skipping {transcript.name}: no text in it.")
        return None

    target = gb.output_path(transcript, args.suffix)
    cache = gb.parts_dir(transcript)
    cache.mkdir(exist_ok=True)

    done = {i for i in range(1, len(chunks) + 1) if gb.part_path(transcript, i).exists()}
    todo = [i for i in range(1, len(chunks) + 1) if i not in done]
    if args.max_chunks:
        todo = todo[: args.max_chunks]

    log(
        f"{transcript.parent.name}: {len(text):,} chars in {len(chunks)} chunk(s); "
        f"{len(done)} cached, sending {len(todo)}."
    )

    for position, index in enumerate(todo):
        previous = gb.part_path(transcript, index - 1)
        tail = None
        if index > 1 and position == 0 and previous.exists():
            tail = previous.read_text(encoding="utf-8").strip()[-args.tail_chars :]
        message = gb.build_message(
            index, len(chunks), chunks[index - 1], tail, gb.resolve_rules(args)
        )

        log(f"  chunk {index}/{len(chunks)} → sending {len(chunks[index - 1]):,} chars")
        t0 = time.time()
        try:
            reply = ask_with_retries(
                app,
                message,
                args,
                fresh=(position == 0),
                chunk=chunks[index - 1],
                must_contain=gb._asr_anchor(chunks[index - 1]),
            )
        except ChunkFailed as exc:
            log(f"  chunk {index} gave up: {exc}")
            if args.stop_on_error:
                raise
            break

        if "##" not in reply:
            log("  WARNING: reply has no Markdown headings.")
        if gb._reply_missing_arabic(reply):
            log(f"  WARNING: translation label without Arabic above it in chunk {index}.")
        gb.part_path(transcript, index).write_text(reply + "\n", encoding="utf-8")
        log(f"  chunk {index}/{len(chunks)} ← got {len(reply):,} chars in {time.time() - t0:.0f}s")
        if index != todo[-1]:
            time.sleep(args.delay)

    have = [i for i in range(1, len(chunks) + 1) if gb.part_path(transcript, i).exists()]
    body = "\n\n".join(
        gb.part_path(transcript, i).read_text(encoding="utf-8").strip() for i in have
    )
    if not have:
        return None
    if len(have) < len(chunks):
        partial = gb.output_path(transcript, gb.partial_suffix(args.suffix))
        partial.write_text(body + "\n", encoding="utf-8")
        log(f"  {len(have)}/{len(chunks)} chunks done → {partial.name} (rerun to finish)")
        return partial

    target.write_text(body + "\n", encoding="utf-8")
    log(f"  wrote {target.name} ({len(body):,} chars)")
    return target


def process_summary(app: GeminiApp, book: Path, args) -> Path | None:
    text = book.read_text(encoding="utf-8").strip()
    if not text:
        log(f"Skipping {book.name}: empty.")
        return None

    target = gb.summary_output_path(book)
    cache = gb.parts_dir(book, gb.SUMMARY_PARTS_PREFIX)
    cache.mkdir(exist_ok=True)
    chunks = gb.split_chunks(text, args.summary_chunk_chars)

    if len(chunks) == 1:
        message = f"{gb.SUMMARY_RULES}\n\n{gb.SUMMARY_HEADER}\n\n{text}"
        reply = ask_with_retries(app, message, args, fresh=True)
        target.write_text(reply + "\n", encoding="utf-8")
        log(f"  wrote {target.name} ({len(reply):,} chars)")
        return target

    todo = [i for i in range(1, len(chunks) + 1) if not (cache / f"part_{i:03d}.md").exists()]
    log(f"{book.parent.name}: summarize {len(text):,} chars, {len(chunks)} chunk(s), sending {len(todo)}.")

    for position, index in enumerate(todo):
        header = f"بخش {index} از {len(chunks)} — فقط یادداشت‌های خلاصه برای این قطعه:"
        message = f"{gb.SUMMARY_RULES}\n\n{header}\n\n{chunks[index - 1]}"
        try:
            reply = ask_with_retries(app, message, args, fresh=(position == 0))
        except ChunkFailed as exc:
            log(f"  summary chunk {index} gave up: {exc}")
            if args.stop_on_error:
                raise
            return None
        (cache / f"part_{index:03d}.md").write_text(reply + "\n", encoding="utf-8")
        if index != todo[-1]:
            time.sleep(args.delay)

    notes = "\n\n".join(
        (cache / f"part_{i:03d}.md").read_text(encoding="utf-8").strip()
        for i in range(1, len(chunks) + 1)
        if (cache / f"part_{i:03d}.md").exists()
    )
    merge_message = (
        f"{gb.SUMMARY_RULES}\n\n"
        "یادداشت‌های خلاصهٔ هر بخش از یک جلسهٔ طولانی:\n\n"
        f"{notes}\n\n"
        "اکنون **یک** فایل خلاصهٔ نهایی با ساختار خواسته‌شده بنویس (بدون تکرار بخش‌ها):"
    )
    reply = ask_with_retries(app, merge_message, args, fresh=True)
    target.write_text(reply + "\n", encoding="utf-8")
    log(f"  wrote {target.name} ({len(reply):,} chars)")
    return target


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", type=Path, help="Transcript file or folder of lectures.")
    p.add_argument("--input-kind", choices=("raw", "any"), default="raw")
    p.add_argument("--summarize", action="store_true", help="Summarize *.book.md instead of building books.")
    p.add_argument("--dry-run", action="store_true", help="Show the plan without touching the app.")
    p.add_argument("--extra-rules", default="", help="Extra style rules appended to the prompt.")

    sel = p.add_argument_group("selection")
    sel.add_argument("--only", nargs="*", default=[])
    sel.add_argument("--start", type=int)
    sel.add_argument("--end", type=int)
    sel.add_argument("--limit", type=int, default=0)
    sel.add_argument("--overwrite", action="store_true")
    sel.add_argument("--max-chunks", type=int, default=0, help="Send at most N chunks per lecture.")

    pace = p.add_argument_group("pacing")
    pace.add_argument("--chunk-chars", type=int, default=6000)
    pace.add_argument("--summary-chunk-chars", type=int, default=12000)
    pace.add_argument("--tail-chars", type=int, default=600)
    pace.add_argument("--delay", type=float, default=4.0, help="Seconds between messages.")
    pace.add_argument("--timeout", type=float, default=900.0, help="Max seconds to wait per reply.")
    pace.add_argument("--retries", type=int, default=3)
    pace.add_argument("--stop-on-error", action="store_true")
    pace.add_argument("--suffix", default=gb.OUTPUT_SUFFIX)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.summarize:
        items = gb.find_book_files(args.target)
        if not args.overwrite:
            items = [b for b in items if not gb.summary_output_path(b).exists()]
    else:
        items = gb.find_transcripts(args.target, args.input_kind)
        items = gb.filter_transcripts(items, args.only, args.start, args.end)
        if not args.overwrite:
            items = [t for t in items if not gb.output_path(t, args.suffix).exists()]

    if args.limit:
        items = items[: args.limit]

    if not items:
        log("Nothing to do.")
        return 0

    log(f"{len(items)} item(s) to process.")
    if args.dry_run:
        for it in items:
            text = gb.continuous_text(it.read_text(encoding="utf-8"))
            budget = args.summary_chunk_chars if args.summarize else args.chunk_chars
            log(f"  {it.parent.name}/{it.name}: {len(text):,} chars → {len(gb.split_chunks(text, budget))} chunk(s)")
        return 0

    app = GeminiApp()
    log(f"Gemini.app pid={app.pid}")

    failures = 0
    for n, item in enumerate(items, 1):
        log(f"[{n}/{len(items)}] {item.name}")
        try:
            if args.summarize:
                process_summary(app, item, args)
            else:
                process_transcript(app, item, args)
        except KeyboardInterrupt:
            log("Interrupted.")
            return 130
        except Exception as exc:  # noqa: BLE001
            failures += 1
            log(f"  FAILED: {exc}")
            if args.stop_on_error:
                return 1
    log(f"Done. {len(items) - failures}/{len(items)} succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
