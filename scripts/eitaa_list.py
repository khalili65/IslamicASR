#!/usr/bin/env python3
"""List the audio posts of a public Eitaa channel.

Usage:
    python scripts/eitaa_list.py shajareh
    python scripts/eitaa_list.py shajareh --pages 20
    python scripts/eitaa_list.py shajareh --pages 20 --json shajareh.json

Reads the public web view (https://eitaa.com/<channel>) and walks backwards
through history with the `?before=` parameter, reporting every post that
carries an audio document. No login is needed and nothing is downloaded —
Eitaa's public HTML lists the file name, duration and size but never a
downloadable URL, so fetching the audio itself needs `eitaa_download.py`.

The message id printed here is what `eitaa_download.py --from-id` expects.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import quote

import requests

BASE_URL = "https://eitaa.com"

# Eitaa serves the public channel view only to browser-looking clients.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

AUDIO_EXTS = (".mp3", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".flac")

# One <div class="... js-widget_message_wrap" id="12345"> per post.
MESSAGE_SPLIT_RE = re.compile(r'js-widget_message_wrap"\s+id="(\d+)"')
DOC_TITLE_RE = re.compile(
    r'etme_widget_message_document_title[^>]*>(.*?)</div>', re.DOTALL
)
DOC_EXTRA_RE = re.compile(
    r'etme_widget_message_document_extra[^>]*>(.*?)</div>', re.DOTALL
)
DATETIME_RE = re.compile(r'<time[^>]+datetime="([^"]+)"')
DURATION_RE = re.compile(r"<time>([^<]+)</time>")
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class AudioPost:
    message_id: int
    filename: str
    duration: str
    size: str
    posted_at: str
    url: str


def strip_tags(fragment: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).split())


def fetch_page(session: requests.Session, channel: str, before: int | None) -> str:
    url = f"{BASE_URL}/{quote(channel)}"
    params = {"before": before} if before else None
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.text


def parse_messages(page_html: str) -> list[tuple[int, str]]:
    """Split a channel page into (message_id, html_fragment) pairs."""
    matches = list(MESSAGE_SPLIT_RE.finditer(page_html))
    messages: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page_html)
        messages.append((int(match.group(1)), page_html[match.start():end]))
    return messages


def parse_audio_post(channel: str, message_id: int, fragment: str) -> AudioPost | None:
    title_match = DOC_TITLE_RE.search(fragment)
    if not title_match:
        return None

    filename = strip_tags(title_match.group(1))
    if not filename.lower().endswith(AUDIO_EXTS):
        return None

    duration = ""
    size = ""
    extra_match = DOC_EXTRA_RE.search(fragment)
    if extra_match:
        extra = extra_match.group(1)
        duration_match = DURATION_RE.search(extra)
        if duration_match:
            duration = html.unescape(duration_match.group(1)).strip()
        # The size sits in a trailing <span>, e.g. "حجم: 24.5M".
        size_match = re.search(r"([\d.]+\s*[KMG])\b", strip_tags(extra))
        if size_match:
            size = size_match.group(1).replace(" ", "")

    posted_at = ""
    datetime_match = DATETIME_RE.search(fragment)
    if datetime_match:
        posted_at = datetime_match.group(1)

    return AudioPost(
        message_id=message_id,
        filename=filename,
        duration=duration,
        size=size,
        posted_at=posted_at,
        url=f"{BASE_URL}/{channel}/{message_id}",
    )


def collect(
    channel: str,
    pages: int,
    delay: float,
    log=print,
) -> list[AudioPost]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Referer": BASE_URL})

    found: dict[int, AudioPost] = {}
    before: int | None = None

    for page in range(1, pages + 1):
        try:
            page_html = fetch_page(session, channel, before)
        except requests.RequestException as exc:
            log(f"  page {page}: request failed ({exc}); stopping")
            break

        messages = parse_messages(page_html)
        if not messages:
            log(f"  page {page}: no posts found; stopping")
            break

        audio_on_page = 0
        for message_id, fragment in messages:
            post = parse_audio_post(channel, message_id, fragment)
            if post and post.message_id not in found:
                found[post.message_id] = post
                audio_on_page += 1

        oldest = min(message_id for message_id, _ in messages)
        log(
            f"  page {page}: posts {oldest}-{max(m for m, _ in messages)}, "
            f"{audio_on_page} audio"
        )

        if before is not None and oldest >= before:
            log("  reached the start of the channel; stopping")
            break
        before = oldest

        if page < pages:
            time.sleep(delay)

    return [found[key] for key in sorted(found, reverse=True)]


def print_table(posts: list[AudioPost]) -> None:
    if not posts:
        print("\nNo audio posts found.")
        return

    id_width = max(len("id"), max(len(str(p.message_id)) for p in posts))
    dur_width = max(len("time"), max(len(p.duration) for p in posts))
    size_width = max(len("size"), max(len(p.size) for p in posts))

    print(f"\n{'id':>{id_width}}  {'time':>{dur_width}}  {'size':>{size_width}}  file")
    print("-" * (id_width + dur_width + size_width + 12))
    for post in posts:
        print(
            f"{post.message_id:>{id_width}}  {post.duration:>{dur_width}}  "
            f"{post.size:>{size_width}}  {post.filename}"
        )
    print(f"\n{len(posts)} audio post(s).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List audio posts in a public Eitaa channel."
    )
    parser.add_argument("channel", help="Channel username, e.g. shajareh")
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="How many history pages to walk back (~12 posts each, default: 5).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between page requests (default: 1.0).",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Also write the results to this JSON file.",
    )
    args = parser.parse_args()

    channel = args.channel.strip().lstrip("@")
    if "/" in channel:
        channel = channel.rstrip("/").split("/")[-1]

    print(f"Channel: {BASE_URL}/{channel}")
    posts = collect(channel, args.pages, args.delay)
    print_table(posts)

    if args.json:
        out_path = Path(args.json).expanduser()
        out_path.write_text(
            json.dumps([asdict(p) for p in posts], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved: {out_path}")

    if posts:
        print(
            "\nEitaa's public view does not expose file URLs. To fetch these, run:\n"
            f"  python scripts/eitaa_download.py {channel} --login   # once\n"
            f"  python scripts/eitaa_download.py {channel} --out Audios/{channel}"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
