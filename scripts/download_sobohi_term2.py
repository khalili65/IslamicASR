#!/usr/bin/env python3
"""Download Sobohi Term2 Manaee audio from alisaboohi.com and remux to *_play.m4a.

Layout: Audios/Tadabor_Sobohi/Manaee/Term2/NNN/NNN_….mp3 (+ NNN_play.m4a)
Session numbers follow فایل N on the course page (001–036).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests

COURSE_PAGE_API = "https://alisaboohi.com/wp-json/wp/v2/pages/5598"
OUTPUT_DIR = Path("Audios/Tadabor_Sobohi/Manaee/Term2")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
DIGIT_TRANS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _get_text(url: str) -> str:
    r = SESSION.get(url, timeout=60)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def normalize_label(label: str) -> str:
    label = unescape(label).replace("&#8211;", "–").replace("&ndash;", "–")
    label = re.sub(r"[\u200c\u200d]", "", label)  # ZWNJ / ZWJ (e.g. فایل۱‍۳)
    label = re.sub(r"\s*\(", " ", label)
    label = label.replace(")", "")
    label = label.replace("–", " - ")
    label = re.sub(r"\s+", " ", label).strip()
    return label


def file_num_from_label(label: str) -> int | None:
    cleaned = re.sub(r"[\u200c\u200d]", "", label)
    m = re.search(r"فایل\s*([۰-۹0-9]+)", cleaned)
    if not m:
        return None
    return int(m.group(1).translate(DIGIT_TRANS))


def make_filename(num: int, label: str) -> str:
    title = normalize_label(label)
    if not title.endswith(" - علی"):
        title = f"{title} - علی"
    # Keep paths sane for the filesystem
    title = title.replace("/", "-").replace("\\", "-")
    if len(title) > 120:
        title = title[:120].rstrip(" ._")
    return f"{num:03d}_{title}.mp3"


def fetch_lectures() -> list[tuple[int, str, str]]:
    """Return (file_num, label, page_url) sorted by file number."""
    r = SESSION.get(COURSE_PAGE_API, timeout=60)
    r.raise_for_status()
    content = r.json()["content"]["rendered"]
    blocks = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', content, re.S)
    base = "https://alisaboohi.com"
    by_num: dict[int, tuple[str, str]] = {}
    for href, inner in blocks:
        label = unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        if "فایل" not in label:
            continue
        if not re.search(r"سطح\s*۲", re.sub(r"[\u200c\u200d]", "", label)):
            continue
        num = file_num_from_label(label)
        if num is None:
            continue
        by_num.setdefault(num, (label, urljoin(base, href)))

    # Course page HTML can drop فایل۱۳ (ZWJ in title); recover via search.
    if 13 not in by_num:
        rr = SESSION.get(
            "https://alisaboohi.com/wp-json/wp/v2/posts",
            params={"search": "قیامت بخش سوم", "per_page": 20},
            timeout=60,
        )
        rr.raise_for_status()
        for post in rr.json():
            title = unescape(post["title"]["rendered"])
            if file_num_from_label(title) == 13 and "سطح۲" in re.sub(
                r"[\u200c\u200d\s]", "", title
            ):
                by_num[13] = (title, post["link"])
                break

    return [(n, *by_num[n]) for n in sorted(by_num)]


def fetch_aparat_hash(page_url: str) -> str | None:
    text = _get_text(page_url)
    m = re.search(r"aparat\.com/video/video/embed/videohash/([a-zA-Z0-9]+)", text)
    return m.group(1) if m else None


def fetch_bayanbox_url(page_url: str) -> str | None:
    text = _get_text(page_url)
    m = re.search(r"(https://bayanbox\.ir/download/[^\s\"'<>]+)", text)
    if not m:
        return None
    url = m.group(1)
    return url if url.endswith(".mp3") else url.rstrip("/") + "/"


def download_file(url: str, dest: Path, retries: int = 3) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with SESSION.get(url, stream=True, timeout=600) as r:
                r.raise_for_status()
                partial = dest.with_suffix(dest.suffix + ".partial")
                with open(partial, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                partial.replace(dest)
            return
        except requests.RequestException as exc:
            last_err = exc
            if attempt + 1 < retries:
                time.sleep(2 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def mp4_to_mp3(src: Path, dest: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )


def remux_play_m4a(mp3: Path) -> Path:
    """Write NNN_play.m4a beside the mp3 (honest AAC duration)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")
    out = mp3.parent / f"{mp3.parent.name}_play.m4a"
    if out.exists() and out.stat().st_size > 100_000:
        if out.stat().st_mtime >= mp3.stat().st_mtime:
            return out
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(mp3),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return out


def download_lecture(num: int, label: str, page_url: str, dest: Path) -> None:
    videohash = fetch_aparat_hash(page_url)
    if videohash:
        api = f"https://www.aparat.com/api/fa/v1/video/video/show/videohash/{videohash}"
        r = SESSION.get(api, timeout=60)
        r.raise_for_status()
        attrs = r.json()["data"]["attributes"]
        links = attrs.get("file_link_all") or []
        by_profile = {item["profile"]: item for item in links if item.get("urls")}
        order = ["360p", "480p", "240p", "720p", "144p", "1080p"]
        profiles = [by_profile[p] for p in order if p in by_profile]
        profiles += [item for item in links if item.get("urls") and item not in profiles]

        tmp_mp4 = dest.with_suffix(".mp4.tmp")
        last_err: Exception | None = None
        for item in profiles:
            mp4_url = item["urls"][0]
            profile = item.get("profile", "?")
            print(f"  [{num:03d}] aparat {videohash} ({profile})", flush=True)
            try:
                download_file(mp4_url, tmp_mp4)
                print(f"  [{num:03d}] extract audio → {dest.name}", flush=True)
                mp4_to_mp3(tmp_mp4, dest)
                tmp_mp4.unlink(missing_ok=True)
                return
            except (requests.RequestException, subprocess.CalledProcessError) as exc:
                last_err = exc
                print(f"  [{num:03d}] {profile} failed ({exc})", flush=True)
                tmp_mp4.unlink(missing_ok=True)

        hls = attrs.get("hls_link")
        if hls:
            print(f"  [{num:03d}] aparat HLS fallback", flush=True)
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("ffmpeg not found on PATH")
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    hls,
                    "-vn",
                    "-acodec",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    str(dest),
                ],
                check=True,
                capture_output=True,
            )
            return
        raise RuntimeError(f"all aparat qualities failed for {videohash}: {last_err}")

    bayanbox = fetch_bayanbox_url(page_url)
    if not bayanbox:
        raise RuntimeError("no aparat embed and no bayanbox mp3 found")
    print(f"  [{num:03d}] bayanbox mp3", flush=True)
    download_file(bayanbox, dest)


def process_one(num: int, label: str, page_url: str, remux: bool) -> str:
    folder = OUTPUT_DIR / f"{num:03d}"
    dest = folder / make_filename(num, label)
    if dest.exists() and dest.stat().st_size > 100_000:
        status = "skip"
    else:
        print(f"[{num:03d}] {normalize_label(label)[:70]}", flush=True)
        print(f"  page: {page_url}", flush=True)
        download_lecture(num, label, page_url, dest)
        status = "ok"
        print(f"  [{num:03d}] done ({dest.stat().st_size / 1e6:.1f} MB)", flush=True)

    if remux:
        play = remux_play_m4a(dest)
        print(f"  [{num:03d}] remux → {play.name} ({play.stat().st_size / 1e6:.1f} MB)", flush=True)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=3, help="Parallel download/remux workers")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=999)
    parser.add_argument("--no-remux", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    lectures = fetch_lectures()
    lectures = [(n, lab, url) for n, lab, url in lectures if args.start <= n <= args.end]
    print(f"Found {len(lectures)} Term2 lectures (files {lectures[0][0]:03d}–{lectures[-1][0]:03d})")
    if args.dry_run:
        for n, lab, url in lectures:
            print(f"  {n:03d}  {normalize_label(lab)[:70]}")
            print(f"       {url}")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = skip = fail = 0
    remux = not args.no_remux

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(process_one, n, lab, url, remux): n for n, lab, url in lectures
        }
        for fut in as_completed(futures):
            n = futures[fut]
            try:
                status = fut.result()
                if status == "ok":
                    ok += 1
                else:
                    skip += 1
            except Exception as exc:  # noqa: BLE001
                print(f"[{n:03d}] ERROR: {exc}", flush=True)
                fail += 1

    print(f"\nFinished: {ok} downloaded, {skip} skipped, {fail} failed")
    # Final pass with the site tool (--force keeps NNN_play.m4a even when
    # the extracted mp3 container duration is already honest).
    if remux and fail == 0:
        print("\nRunning prepare_playback.py --force for Term2…")
        subprocess.run(
            [
                sys.executable,
                "website/tools/prepare_playback.py",
                "--course",
                str(OUTPUT_DIR),
                "--force",
            ],
            check=False,
        )
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
