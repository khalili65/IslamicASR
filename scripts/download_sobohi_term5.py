#!/usr/bin/env python3
"""End-to-end Term5 Sobohi Manaee: Shenoto download → remux → ElevenLabs ASR.

Primary layout on box (mirrors Mac):
  /workspace/IslamASR_mirror/Audios/Tadabor_Sobohi/Manaee/Term5/NNN/
Also writes map/log next to Term5.
"""
from __future__ import annotations

import json
import os
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

ROOT = Path(os.environ.get("ISLAMASR_ROOT", "/workspace/IslamASR_mirror"))
COURSE = ROOT / "Audios/Tadabor_Sobohi/Manaee/Term5"
MAP_PATH = ROOT / "Audios/Tadabor_Sobohi/Manaee/Term5_shenoto_map.json"
LOG_PATH = ROOT / "Audios/Tadabor_Sobohi/Manaee/Term5_pipeline.log"
COURSE_PAGE_API = "https://alisaboohi.com/wp-json/wp/v2/pages/11185"
VENV_PY = Path(os.environ.get("ISLAMASR_VENV_PY", "/workspace/.venv/bin/python"))
PREPARE_PLAYBACK = Path(
    os.environ.get(
        "ISLAMASR_PREPARE_PLAYBACK",
        "/workspace/IslamASR_mirror/website/tools/prepare_playback.py",
    )
)
# fallback to islam_asr_tools
if not PREPARE_PLAYBACK.exists():
    PREPARE_PLAYBACK = Path("/workspace/islam_asr_tools/prepare_playback.py")
TRANSCRIBE = Path(os.environ.get("ISLAMASR_TRANSCRIBE", "/workspace/IslamASR_mirror/transcribe.py"))

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
DIGIT_TRANS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
SHENOTO_HDR = {
    "Accept": "application/json",
    "Origin": "https://iframe.shenoto.net",
    "Referer": "https://iframe.shenoto.net/",
}


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> int:
        for s in self.streams:
            s.write(data)
            s.flush()
        return len(data)

    def flush(self) -> None:
        for s in self.streams:
            s.flush()


def log(msg: str) -> None:
    print(msg, flush=True)


def normalize_label(label: str) -> str:
    label = unescape(label).replace("&#8211;", "–").replace("&ndash;", "–")
    label = re.sub(r"[\u200c\u200d]", "", label)
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
    title = title.replace("/", "-").replace("\\", "-")
    if len(title) > 120:
        title = title[:120].rstrip(" ._")
    return f"{num:03d}_{title}.mp3"


def build_map() -> list[dict]:
    r = SESSION.get(COURSE_PAGE_API, timeout=60)
    r.raise_for_status()
    content = r.json()["content"]["rendered"]
    ids = re.findall(r"shenoto\.com/player/podcast/(\d+)", content)
    blocks = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', content, re.S)
    by_num: dict[int, tuple[str, str]] = {}
    for href, inner in blocks:
        label = unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        cleaned = re.sub(r"[\u200c\u200d]", "", label)
        if "فایل" not in cleaned:
            continue
        if not re.search(r"سطح\s*۵", cleaned):
            continue
        num = file_num_from_label(label)
        if num is None:
            continue
        by_num.setdefault(num, (label, urljoin("https://alisaboohi.com", href)))
    if len(ids) != 31:
        raise RuntimeError(f"expected 31 shenoto ids, got {len(ids)}")
    if len(by_num) != 31:
        raise RuntimeError(f"expected 31 labels, got {len(by_num)}")
    items = []
    for i, pid in enumerate(ids):
        num = i + 1
        label, page = by_num[num]
        album_url = f"https://shenoto.com/service/api/mss/podcast/album/{pid}?agent=shenoto-iframe"
        ar = SESSION.get(album_url, headers=SHENOTO_HDR, timeout=60)
        ar.raise_for_status()
        album = ar.json()
        data = album.get("album") or album.get("data") or album
        medias = (data or {}).get("medias") if isinstance(data, dict) else None
        if not medias:
            medias = album.get("medias")
        if not medias:
            raise RuntimeError(f"no medias for pid={pid}")
        items.append(
            {
                "num": num,
                "pid": pid,
                "title": label,
                "page": page,
                "file": medias[0]["file"],
            }
        )
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    # also copy to /workspace
    Path("/workspace/Term5_shenoto_map.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return items


def resolve_cdn(file_api_url: str) -> str:
    r = SESSION.get(
        file_api_url,
        params={"agent": "shenoto-iframe", "fetch": "true"},
        headers=SHENOTO_HDR,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    link = data.get("link") or (data.get("data") or {}).get("link")
    if not link:
        raise RuntimeError(f"no link in {data}")
    return link


def download_file(url: str, dest: Path, retries: int = 4) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with SESSION.get(url, stream=True, timeout=600) as r:
                if r.status_code == 404:
                    raise FileNotFoundError(f"CDN 404: {url}")
                r.raise_for_status()
                partial = dest.with_suffix(dest.suffix + ".partial")
                with open(partial, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                if partial.stat().st_size < 100_000:
                    partial.unlink(missing_ok=True)
                    raise RuntimeError(f"downloaded too small: {partial.stat().st_size if partial.exists() else 0}")
                partial.replace(dest)
            return
        except FileNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def fetch_aparat_hash(page_url: str) -> str | None:
    r = SESSION.get(page_url, timeout=60)
    r.raise_for_status()
    m = re.search(r"aparat\.com/video/video/embed/videohash/([a-zA-Z0-9]+)", r.text)
    return m.group(1) if m else None


def fetch_bayanbox_url(page_url: str) -> str | None:
    r = SESSION.get(page_url, timeout=60)
    r.raise_for_status()
    m = re.search(r"(https://bayanbox\.ir/download/[^\s\"'<>]+)", r.text)
    return m.group(1) if m else None


def aparat_to_mp3(videohash: str, dest: Path) -> None:
    # use aparat API for lowest workable mp4 then ffmpeg extract
    api = f"https://www.aparat.com/api/fa/v1/video/video/show/videohash/{videohash}"
    r = SESSION.get(api, timeout=60)
    r.raise_for_status()
    data = r.json()
    # find file link
    links = []
    try:
        multi = data["data"]["attributes"]["file_link_all"]
        for item in multi:
            links.append((item.get("profile", ""), item["urls"][0]))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"aparat parse fail: {exc}") from exc
    # prefer 144p/240p/360p
    prefer = ["144p", "240p", "360p", "480p", "720p"]
    url = None
    for p in prefer:
        for profile, u in links:
            if p in str(profile):
                url = u
                break
        if url:
            break
    if not url and links:
        url = links[0][1]
    if not url:
        raise RuntimeError("no aparat url")
    tmp_mp4 = dest.with_suffix(".mp4.tmp")
    download_file(url, tmp_mp4)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg missing")
    subprocess.run(
        [ffmpeg, "-y", "-i", str(tmp_mp4), "-vn", "-acodec", "libmp3lame", "-q:a", "4", str(dest)],
        check=True,
        capture_output=True,
    )
    tmp_mp4.unlink(missing_ok=True)


def download_one(item: dict) -> str:
    num = int(item["num"])
    label = item["title"]
    folder = COURSE / f"{num:03d}"
    dest = folder / make_filename(num, label)
    if dest.exists() and dest.stat().st_size > 100_000:
        log(f"[{num:03d}] skip existing mp3 ({dest.stat().st_size/1e6:.1f} MB)")
        return "skip"
    log(f"[{num:03d}] shenoto {item['pid']} → {dest.name[:70]}")
    try:
        cdn = resolve_cdn(item["file"])
        log(f"  [{num:03d}] cdn {cdn[:90]}")
        download_file(cdn, dest)
        log(f"  [{num:03d}] ok ({dest.stat().st_size/1e6:.1f} MB)")
        return "ok"
    except Exception as exc:  # noqa: BLE001
        log(f"  [{num:03d}] Shenoto failed: {exc}; trying fallbacks")
        # bayanbox
        try:
            burl = fetch_bayanbox_url(item["page"])
            if burl:
                log(f"  [{num:03d}] bayanbox")
                download_file(burl, dest)
                if dest.exists() and dest.stat().st_size > 100_000:
                    log(f"  [{num:03d}] bayanbox ok ({dest.stat().st_size/1e6:.1f} MB)")
                    return "ok-bayanbox"
        except Exception as exc2:  # noqa: BLE001
            log(f"  [{num:03d}] bayanbox fail: {exc2}")
        # aparat
        try:
            vh = fetch_aparat_hash(item["page"])
            if not vh:
                raise RuntimeError("no aparat hash")
            log(f"  [{num:03d}] aparat {vh}")
            aparat_to_mp3(vh, dest)
            log(f"  [{num:03d}] aparat ok ({dest.stat().st_size/1e6:.1f} MB)")
            return "ok-aparat"
        except Exception as exc3:  # noqa: BLE001
            log(f"  [{num:03d}] aparat fail: {exc3}")
            raise RuntimeError(f"all sources failed for {num:03d}: {exc}") from exc3


def remux_all() -> None:
    log("=== remux prepare_playback --force ===")
    COURSE.mkdir(parents=True, exist_ok=True)
    # prepare_playback expects relative course under a repo root; emulate Mac layout
    # Prefer calling with absolute via --course if script supports path; Term3 used relative from repo.
    # Our prepare_playback copy:
    cmd = [
        str(VENV_PY if VENV_PY.exists() else sys.executable),
        str(PREPARE_PLAYBACK),
        "--course",
        str(COURSE),
        "--force",
    ]
    # Also try relative form from ROOT
    env = os.environ.copy()
    log("running: " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    sys.stdout.write(proc.stdout or "")
    sys.stderr.write(proc.stderr or "")
    if proc.returncode != 0:
        # fallback: local ffmpeg remux like Term3 script
        log(f"prepare_playback exited {proc.returncode}; falling back to ffmpeg remux")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg not found")
        for folder in sorted(COURSE.glob("[0-9][0-9][0-9]")):
            mp3s = [p for p in folder.glob("*.mp3") if not p.name.endswith(".partial")]
            if not mp3s:
                continue
            mp3 = mp3s[0]
            out = folder / f"{folder.name}_play.m4a"
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
            log(f"  remux {folder.name} → {out.name} ({out.stat().st_size/1e6:.1f} MB)")
    else:
        log("prepare_playback ok")


def run_asr() -> tuple[int, int, int]:
    log("=== ElevenLabs ASR ===")
    # load env
    env_file = Path("/workspace/IslamASR_box/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    ok = skip = fail = 0
    py = str(VENV_PY if VENV_PY.exists() else sys.executable)
    for folder in sorted(COURSE.glob("[0-9][0-9][0-9]")):
        mp3s = [p for p in folder.glob("*.mp3") if "_play" not in p.name]
        if not mp3s:
            log(f"[{folder.name}] no mp3")
            fail += 1
            continue
        mp3 = mp3s[0]
        txt = mp3.with_suffix(".txt")
        if txt.exists() and txt.stat().st_size >= 500:
            log(f"[{folder.name}] skip ASR (txt {txt.stat().st_size} bytes)")
            skip += 1
            continue
        log(f"[{folder.name}] ASR → {txt.name[:60]}")
        proc = subprocess.run(
            [py, str(TRANSCRIBE), str(mp3), "--provider", "elevenlabs", "--language", "fa"],
            cwd=str(TRANSCRIBE.parent),
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            log(proc.stdout[-500:])
        if proc.returncode != 0:
            log(f"[{folder.name}] ASR FAIL rc={proc.returncode}: {(proc.stderr or '')[-400:]}")
            fail += 1
            continue
        if not txt.exists() or txt.stat().st_size < 500:
            # transcribe may write beside mp3 with same stem — already checked
            # sometimes writes differently
            alts = list(folder.glob("*.txt"))
            good = [a for a in alts if a.stat().st_size >= 500 and not a.name.endswith(".partial.txt")]
            if good:
                log(f"[{folder.name}] ASR ok via {good[0].name} ({good[0].stat().st_size})")
                ok += 1
            else:
                log(f"[{folder.name}] ASR produced no/small txt")
                fail += 1
        else:
            log(f"[{folder.name}] ASR ok ({txt.stat().st_size} bytes)")
            ok += 1
    return ok, skip, fail


def inventory() -> dict:
    counts = {"folders": 0, "mp3": 0, "m4a": 0, "txt": 0, "missing": []}
    for n in range(1, 32):
        folder = COURSE / f"{n:03d}"
        if not folder.is_dir():
            counts["missing"].append(f"{n:03d}:no-folder")
            continue
        counts["folders"] += 1
        mp3 = list(folder.glob("*.mp3"))
        m4a = list(folder.glob("*_play.m4a"))
        txt = [p for p in folder.glob("*.txt") if p.stat().st_size >= 500]
        if mp3:
            counts["mp3"] += 1
        else:
            counts["missing"].append(f"{n:03d}:mp3")
        if m4a:
            counts["m4a"] += 1
        else:
            counts["missing"].append(f"{n:03d}:m4a")
        if txt:
            counts["txt"] += 1
        else:
            counts["missing"].append(f"{n:03d}:txt")
    return counts


def main() -> int:
    COURSE.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_f = open(LOG_PATH, "a", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_f)  # type: ignore[assignment]
    sys.stderr = Tee(sys.__stderr__, log_f)  # type: ignore[assignment]
    log(f"=== Term5 pipeline start {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    log(f"ROOT={ROOT} COURSE={COURSE}")

    if MAP_PATH.exists():
        items = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        log(f"loaded map {len(items)} from {MAP_PATH}")
    else:
        items = build_map()
        log(f"built map {len(items)}")

    # download (parallel for speed, like Term3)
    ok = skip = fail = 0
    failed_nums = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(download_one, it): it["num"] for it in items}
        for fut in as_completed(futs):
            n = futs[fut]
            try:
                st = fut.result()
                if st == "skip":
                    skip += 1
                else:
                    ok += 1
            except Exception as exc:  # noqa: BLE001
                log(f"[{n:03d}] ERROR: {exc}")
                fail += 1
                failed_nums.append(n)
    log(f"Download done: ok={ok} skip={skip} fail={fail} failed={failed_nums}")

    # ensure 31 mp3 before remux
    mp3_count = sum(1 for n in range(1, 32) if list((COURSE / f"{n:03d}").glob("*.mp3")))
    log(f"mp3 present: {mp3_count}/31")
    if mp3_count == 31:
        remux_all()
    else:
        log("SKIP remux: not all mp3 present")

    if os.environ.get("TERM5_SKIP_ASR", "").strip() in {"1", "true", "yes"}:
        log("SKIP ASR (TERM5_SKIP_ASR set)")
        asr_ok = asr_skip = asr_fail = 0
    else:
        asr_ok, asr_skip, asr_fail = run_asr()
        log(f"ASR done: ok={asr_ok} skip={asr_skip} fail={asr_fail}")

    inv = inventory()
    log(f"INVENTORY: {json.dumps(inv, ensure_ascii=False)}")
    all_good = inv["mp3"] == 31 and inv["m4a"] == 31 and inv["txt"] == 31 and not inv["missing"]
    if all_good:
        log("ALL DONE mp3=31 m4a=31 txt=31")
        return 0
    log(f"ALL DONE WITH GAPS missing={inv['missing']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
