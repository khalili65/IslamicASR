#!/usr/bin/env python3
"""Convert IslamASR raw transcript Segments block to SRT beside the .txt."""
from __future__ import annotations
import re, sys
from pathlib import Path

pat = re.compile(r"\[\s*([0-9.]+)s\s*-\s*([0-9.]+)s\]\s*(.*)")

def convert(txt_path: Path) -> Path | None:
    text = txt_path.read_text(encoding="utf-8")
    words = []
    in_seg = False
    for line in text.splitlines():
        if line.strip() == "--- Segments ---":
            in_seg = True
            continue
        if not in_seg:
            continue
        m = pat.match(line.strip())
        if not m:
            continue
        s, e, w = float(m.group(1)), float(m.group(2)), m.group(3).strip()
        if w:
            words.append((s, e, w))
    if not words:
        return None
    cues, cur = [], []
    MAX_WORDS, MAX_DUR, PAUSE = 10, 4.8, 0.55
    def flush():
        nonlocal cur
        if not cur:
            return
        cues.append((cur[0][0], max(cur[-1][1], cur[0][0] + 0.4), " ".join(w for _, _, w in cur)))
        cur = []
    for s, e, w in words:
        if not cur:
            cur = [(s, e, w)]
            continue
        if s - cur[-1][1] >= PAUSE or len(cur) >= MAX_WORDS or e - cur[0][0] >= MAX_DUR:
            flush()
            cur = [(s, e, w)]
        else:
            cur.append((s, e, w))
    flush()
    def fmt(t: float) -> str:
        t = max(0.0, t)
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        sec = t % 60
        return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
    lines = []
    for i, (s, e, body) in enumerate(cues, 1):
        if e <= s:
            e = s + 0.4
        lines += [str(i), f"{fmt(s)} --> {fmt(e)}", body, ""]
    srt = txt_path.with_suffix(".srt")
    srt.write_text("\n".join(lines), encoding="utf-8")
    print(f"[srt] {srt} cues={len(cues)}")
    return srt

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        convert(Path(arg))
