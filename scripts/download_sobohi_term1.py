#!/usr/bin/env python3
"""Download Sobohi Term1 Manaee audio files from alisaboohi.com."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from html import unescape
from pathlib import Path

import requests

COURSE_URL = (
    "https://alisaboohi.com/%d8%aa%d8%af%d8%b1%db%8c%d8%b3%d9%87%d8%a7%db%8c-%d8%b9%d9%84%db%8c-"
    "%d8%b5%d8%a8%d9%88%d8%ad%db%8c-%d8%b7%d8%b3%d9%88%d8%ac%db%8c/%d8%af%d9%88%d8%b1%d9%87%d9%87"
    "%d8%a7%db%8c-%d8%a2%d9%85%d9%88%d8%b2%d8%b4%db%8c/%d8%af%d9%88%d8%b1%d9%87%e2%80%8c%d9%87"
    "%d8%a7%db%8c-%d9%85%d8%b9%d8%b1%d9%81%d8%aa%db%8c-%d8%aa%d8%af%d8%a8%d8%b1-%d8%af%d8%b1-%d9%82%d8%b1"
    "%d8%a2%d9%86-%da%a9%d8%b1%db%8c%d9%85/%d8%af%d9%88%d8%b1%d9%87-%d8%b3%d8%b7%d8%ad-%db%8c%da%a9-"
    "%d8%aa%d8%af%d8%a8%d8%b1-%d8%af%d8%b1-%d9%82%d8%b1%d8%a2%d9%86-%da%a9%d8%b1%db%8c%d9%85-"
    "%d8%b3%d9%88%d8%b1%d9%87%e2%80%8c%d9%87%d8%a7%db%8c/"
)
OUTPUT_DIR = Path("Audios/Tadabor_Sobohi/Manaee/Term1")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})


def _get_text(url: str) -> str:
    r = SESSION.get(url, timeout=60)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def normalize_label(label: str) -> str:
    label = unescape(label).replace("&#8211;", "–").replace("&ndash;", "–")
    label = re.sub(r"\s*\(", " ", label)
    label = label.replace(")", "")
    label = label.replace("–", " - ")
    label = re.sub(r"\s+", " ", label).strip()
    return label


def file_num_from_label(label: str) -> int | None:
    m = re.search(r"فایل\s*([۰-۹0-9]+)", label)
    if not m:
        return None
    digits = m.group(1)
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return int(digits.translate(trans))


def make_filename(num: int, label: str) -> str:
    title = normalize_label(label)
    if not title.endswith(" - علی"):
        title = f"{title} - علی"
    return f"{num:03d}_{title}.mp3"


def fetch_lectures() -> list[tuple[str, str]]:
    text = _get_text(COURSE_URL)
    blocks = re.findall(r'<a[^>]+href="([^"]+)"[^>]*aria-label="([^"]+)"', text)
    seen: set[str] = set()
    lectures: list[tuple[str, str]] = []
    for url, label in blocks:
        label = unescape(label)
        if "فایل" in label and url not in seen:
            seen.add(url)
            lectures.append((label, url))
    return lectures


def fetch_bayanbox_url(page_url: str) -> str | None:
    text = _get_text(page_url)
    m = re.search(r"(https://bayanbox\.ir/download/[^\s\"'<>]+)", text)
    if not m:
        return None
    url = m.group(1)
    return url if url.endswith(".mp3") else url.rstrip("/") + "/"


def fetch_aparat_hash(page_url: str) -> str | None:
    text = _get_text(page_url)
    m = re.search(r"aparat\.com/video/video/embed/videohash/([a-zA-Z0-9]+)", text)
    return m.group(1) if m else None


def download_file(url: str, dest: Path, retries: int = 3) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with SESSION.get(url, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
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
        [ffmpeg, "-y", "-i", str(src), "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(dest)],
        check=True,
        capture_output=True,
    )


def download_lecture(num: int, label: str, page_url: str, dest: Path) -> None:
    # Prefer Aparat (reachable); bayanbox.ir often fails DNS outside Iran.
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
            print(f"  aparat {videohash} ({profile}): downloading video...")
            try:
                download_file(mp4_url, tmp_mp4)
                print(f"  extracting audio -> {dest.name}")
                mp4_to_mp3(tmp_mp4, dest)
                tmp_mp4.unlink(missing_ok=True)
                return
            except requests.RequestException as exc:
                last_err = exc
                print(f"  {profile} failed ({exc}), trying next quality...")
                tmp_mp4.unlink(missing_ok=True)

        hls = attrs.get("hls_link")
        if hls:
            print(f"  aparat {videohash}: progressive failed, trying HLS...")
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("ffmpeg not found on PATH")
            subprocess.run(
                [ffmpeg, "-y", "-i", hls, "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(dest)],
                check=True,
                capture_output=True,
            )
            return

        raise RuntimeError(f"all aparat qualities failed for {videohash}: {last_err}")

    bayanbox = fetch_bayanbox_url(page_url)
    if not bayanbox:
        raise RuntimeError("no aparat embed and no bayanbox mp3 found")
    print("  no aparat embed; trying bayanbox...")
    download_file(bayanbox, dest)


def main() -> int:
    start_from = int(sys.argv[1]) if len(sys.argv) > 1 else 17
    lectures = fetch_lectures()
    print(f"Found {len(lectures)} lectures on course page")

    ok, skip, fail = 0, 0, 0
    for label, page_url in lectures:
        num = file_num_from_label(label)
        if num is None or num < start_from:
            continue

        folder = OUTPUT_DIR / f"{num:03d}"
        filename = make_filename(num, label)
        dest = folder / filename

        if dest.exists() and dest.stat().st_size > 100_000:
            print(f"[skip] {num:03d} already exists")
            skip += 1
            continue

        print(f"[{num:03d}] {normalize_label(label)[:70]}")
        print(f"  page: {page_url}")
        try:
            download_lecture(num, label, page_url, dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"  done ({size_mb:.1f} MB)")
            ok += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  ERROR: {e}")
            fail += 1

    print(f"\nFinished: {ok} downloaded, {skip} skipped, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
