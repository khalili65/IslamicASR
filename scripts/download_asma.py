#!/usr/bin/env python3
import concurrent.futures, subprocess, time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote

COURSE = Path("/Users/mohammadreza/IslamASR/Audios/AyatollahShojaee/Asma_hosna")
MANIFEST = Path("/Users/mohammadreza/IslamASR/_agent_scratch/asma_manifest.tsv")
LOG = COURSE / "download.log"
JOBS = 6

def encode_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%"), quote(parts.query, safe="=&%"), parts.fragment))

rows = []
for line in MANIFEST.read_text().splitlines():
    n, url, title = line.split("\t", 2)
    rows.append((int(n), url, title))

def one(row):
    n, url, title = row
    d = COURSE / f"{n:03d}"
    d.mkdir(exist_ok=True)
    dest = d / f"{n:03d}_{title}"
    if dest.exists() and dest.stat().st_size > 50000:
        return ("skip", n)
    tmp = dest.with_suffix(".mp3.tmp")
    enc = encode_url(url)
    for attempt in range(1, 4):
        r = subprocess.run(
            ["curl", "-fL", "--retry", "2", "--connect-timeout", "30", "--max-time", "600",
             "-A", "Mozilla/5.0", "-o", str(tmp), enc],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 50000:
            with open(tmp, "rb") as f:
                head = f.read(3)
            if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xfa", b"\xff\xf2"):
                tmp.replace(dest)
                with open(LOG, "a") as log:
                    log.write(f"[ok] {n:03d} {dest.stat().st_size}\n")
                return ("ok", n)
        time.sleep(attempt)
    with open(LOG, "a") as log:
        log.write(f"[FAIL] {n:03d} {url}\n")
    return ("fail", n)

LOG.write_text("")
print(f"downloading {len(rows)} jobs={JOBS}", flush=True)
ok = fail = skip = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=JOBS) as ex:
    futs = [ex.submit(one, row) for row in rows]
    for fut in concurrent.futures.as_completed(futs):
        st, n = fut.result()
        if st == "ok": ok += 1
        elif st == "fail": fail += 1
        else: skip += 1
        done = ok + fail + skip
        if done % 10 == 0 or done == len(rows):
            print(f"progress {done}/{len(rows)} ok={ok} skip={skip} fail={fail}", flush=True)
print(f"DOWNLOAD_DONE ok={ok} skip={skip} fail={fail} total={len(rows)}", flush=True)
