#!/usr/bin/env python3
import concurrent.futures, subprocess, time
from pathlib import Path

ROOT = Path("/Users/mohammadreza/IslamASR")
COURSE = ROOT / "Audios/AyatollahShojaee/Asma_hosna"
LOG = COURSE / "pipeline.log"
N = 18
JOBS = 2
VENV_PY = str(ROOT / ".venv/bin/python")

def log(msg: str) -> None:
    with open(LOG, "a") as f:
        f.write(msg + "\n")
    print(msg, flush=True)

def wait_download():
    log(f"=== wait download {time.strftime('%c')} ===")
    while True:
        if (COURSE / "download.log").exists():
            text = (COURSE / "download.log").read_text()
            if "DOWNLOAD_DONE" in text:
                log("download ready")
                return
        time.sleep(5)

def remux():
    log(f"=== remux {time.strftime('%c')} ===")
    r = subprocess.run(
        [VENV_PY, str(ROOT / "website/tools/prepare_playback.py"), "--course", str(COURSE.relative_to(ROOT)), "--force"],
        cwd=ROOT, capture_output=True, text=True,
    )
    log(r.stdout[-2000:] if r.stdout else "")
    if r.stderr:
        log(r.stderr[-1000:])
    log(f"remux exit={r.returncode}")

def missing() -> list[str]:
    out = []
    for i in range(1, N + 1):
        d = f"{i:03d}"
        folder = COURSE / d
        txts = [p for p in folder.glob("*.txt") if "partial" not in p.name and p.stat().st_size > 1024]
        if not txts:
            out.append(d)
    return out

def work_one(d: str) -> str:
    folder = COURSE / d
    mp3s = list(folder.glob("*.mp3"))
    if not mp3s:
        log(f"[no-mp3] {d}")
        return "no-mp3"
    mp3 = mp3s[0]
    txt = mp3.with_suffix(".txt")
    if txt.exists() and txt.stat().st_size > 1024:
        log(f"[skip] {d}")
        subprocess.run([VENV_PY, str(ROOT / "scripts/txt_to_srt.py"), str(txt)], cwd=ROOT)
        return "skip"
    log(f"[start] {d} {time.strftime('%c')}")
    tlog = folder / "transcribe.log"
    with open(tlog, "a") as lf:
        r = subprocess.run(
            [VENV_PY, str(ROOT / "transcribe.py"), str(mp3), "--provider", "elevenlabs", "--language", "fa"],
            cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT,
        )
    if r.returncode == 0 and txt.exists() and txt.stat().st_size > 1024:
        log(f"[ok] {d} {time.strftime('%c')}")
        subprocess.run([VENV_PY, str(ROOT / "scripts/txt_to_srt.py"), str(txt)], cwd=ROOT)
        return "ok"
    log(f"[FAIL] {d} {time.strftime('%c')}")
    return "fail"

LOG.write_text("")
wait_download()
remux()
log(f"=== ASR start {time.strftime('%c')} N={N} jobs={JOBS} ===")
round_n = 0
while True:
    miss = missing()
    log(f"[{time.strftime('%c')}] missing={len(miss)} round={round_n}")
    if not miss:
        log(f"ASR_ALL_DONE {time.strftime('%c')}")
        break
    with concurrent.futures.ThreadPoolExecutor(max_workers=JOBS) as ex:
        list(ex.map(work_one, miss))
    round_n += 1
    if round_n >= 40:
        log(f"ASR_GAVE_UP {time.strftime('%c')}")
        break
    time.sleep(15)
log(f"PIPELINE_DONE {time.strftime('%c')}")
