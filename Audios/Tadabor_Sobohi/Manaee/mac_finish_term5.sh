#!/bin/bash
set -euo pipefail
ROOT="/Users/mohammadreza/IslamASR"
MANAEE="$ROOT/Audios/Tadabor_Sobohi/Manaee"
cd "$ROOT"

# 1) Transcripts + map + script
TXT_TAR="$MANAEE/Term5_txts_and_meta.tar.gz"
if [[ -f "$TXT_TAR" ]]; then
  tar xzf "$TXT_TAR"
  echo "Extracted transcripts/map/script"
fi

# 2) Audio parts → tar → extract
cd "$MANAEE"
if [[ -f Term5_audio.tar.part00 ]]; then
  cat Term5_audio.tar.part* > Term5_audio.tar
  tar xf Term5_audio.tar -C "$ROOT"
  echo "Extracted audio (mp3 + play.m4a)"
  rm -f Term5_audio.tar
fi

python3 - <<'PY'
from pathlib import Path
c=Path("/Users/mohammadreza/IslamASR/Audios/Tadabor_Sobohi/Manaee/Term5")
for kind, pat, minb in [("mp3","*.mp3",100000),("m4a","*_play.m4a",50000),("txt","*.txt",500)]:
    n=sum(1 for p in c.glob(f"*/{pat}") if p.stat().st_size>=minb)
    print(f"{kind}={n}/31")
missing=[]
for i in range(1,32):
    d=c/f"{i:03d}"
    if not d.is_dir():
        missing.append(f"{i:03d}:dir"); continue
    for kind, pat, minb in [("mp3","*.mp3",100000),("m4a","*_play.m4a",50000),("txt","*.txt",500)]:
        if not any(p.stat().st_size>=minb for p in d.glob(pat)):
            missing.append(f"{i:03d}:{kind}")
print("missing:", missing or "none")
PY
