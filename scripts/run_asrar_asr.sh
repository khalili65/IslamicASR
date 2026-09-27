#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate
COURSE="Audios/AyatollahShojaee/AsrarFatemi"
LOG="$COURSE/asr.log"
JOBS=2
echo "=== Asrar ASR start $(date) ===" | tee -a "$LOG"

missing_count() {
  local n=0 d
  for d in $(seq -f '%03g' 1 9); do
    if ! find "$COURSE/$d" -maxdepth 1 -name '*.txt' ! -name '*partial*' -size +1k 2>/dev/null | grep -q .; then
      n=$((n+1))
    fi
  done
  echo "$n"
}

work_one() {
  local n="$1" d dir mp3 txt
  d=$(printf "%03d" "$n")
  dir="$COURSE/$d"
  mp3=$(ls "$dir"/*.mp3 2>/dev/null | head -1 || true)
  [ -z "${mp3:-}" ] && return 0
  txt="${mp3%.mp3}.txt"
  # if mp3 name is 001_title.mp3, txt beside it
  # actually mp3 path may not match - find mp3 and set txt next to it
  txt="${mp3%.mp3}.txt"
  if [ -s "$txt" ]; then
    echo "[skip] $d" | tee -a "$LOG"
    python scripts/txt_to_srt.py "$txt" >>"$LOG" 2>&1 || true
    return 0
  fi
  echo "[start] $d $(date)" | tee -a "$LOG"
  if python transcribe.py "$mp3" --provider elevenlabs --language fa >>"$dir/transcribe.log" 2>&1; then
    echo "[ok] $d $(date)" | tee -a "$LOG"
    python scripts/txt_to_srt.py "$txt" >>"$LOG" 2>&1 || true
  else
    echo "[FAIL] $d $(date)" | tee -a "$LOG"
    return 1
  fi
}
export -f work_one
export COURSE LOG
export PATH="$ROOT/.venv/bin:$PATH"

round=0
while true; do
  miss=$(missing_count)
  echo "[$(date)] missing=$miss round=$round" | tee -a "$LOG"
  [ "$miss" -eq 0 ] && { echo "ASR_ALL_DONE $(date)" | tee -a "$LOG"; break; }
  seq 1 9 | xargs -P "$JOBS" -n 1 bash -c 'source "'"$ROOT"'/.venv/bin/activate"; work_one "$1"' _
  round=$((round+1))
  [ "$round" -ge 20 ] && { echo "ASR_GAVE_UP $(date)" | tee -a "$LOG"; break; }
  sleep 15
done
