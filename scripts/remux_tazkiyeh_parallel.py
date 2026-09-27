#!/usr/bin/env python3
import concurrent.futures, subprocess, tempfile, time
from pathlib import Path

COURSE = Path("/Users/mohammadreza/IslamASR/Audios/AyatollahShojaee/Tazkiyeh")
LOG = COURSE / "remux_parallel.log"
JOBS = 6

def one(n: int):
    d = COURSE / f"{n:03d}"
    mp3s = list(d.glob("*.mp3"))
    if not mp3s:
        return ("nomp3", n)
    src = mp3s[0]
    dest = d / f"{n:03d}_play.m4a"
    if dest.exists() and dest.stat().st_size > 10000 and dest.stat().st_mtime >= src.stat().st_mtime:
        return ("skip", n)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "play.m4a"
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-vn", "-map", "0:a:0", "-map_metadata", "-1",
                "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                str(tmp_out),
            ],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not tmp_out.exists() or tmp_out.stat().st_size < 1000:
            with open(LOG, "a") as log:
                log.write(f"[FAIL] {n:03d}\n{proc.stderr[-400:]}\n")
            return ("fail", n)
        dest.write_bytes(tmp_out.read_bytes())
    with open(LOG, "a") as log:
        log.write(f"[ok] {n:03d} {time.time()-t0:.1f}s {dest.stat().st_size}\n")
    return ("ok", n)

todo = list(range(1, 142))
print(f"jobs={JOBS} todo={len(todo)}", flush=True)
ok = fail = skip = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=JOBS) as ex:
    futs = [ex.submit(one, n) for n in todo]
    for fut in concurrent.futures.as_completed(futs):
        st, n = fut.result()
        if st == "ok":
            ok += 1
        elif st == "fail":
            fail += 1
        else:
            skip += 1
        done = ok + fail + skip
        if done % 10 == 0 or done == len(todo):
            print(f"progress {done}/{len(todo)} ok={ok} skip={skip} fail={fail}", flush=True)
print(f"REMUX_DONE ok={ok} skip={skip} fail={fail}", flush=True)
