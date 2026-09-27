#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate
COURSE="Audios/AyatollahShojaee/Tazkiyeh"
LOG="$COURSE/asr_overnight.log"
JOBS=2
echo "=== overnight ASR start $(date) ===" | tee -a "$LOG"

missing_count() {
  local n=0 d
  for d in $(seq -f '%03g' 1 141); do
    if ! find "$COURSE/$d" -maxdepth 1 -name '*.txt' ! -name '*partial*' -size +1k 2>/dev/null | grep -q .; then
      n=$((n+1))
    fi
  done
  echo "$n"
}

round=0
while true; do
  miss=$(missing_count)
  echo "[$(date)] missing=$miss round=$round" | tee -a "$LOG"
  if [ "$miss" -eq 0 ]; then
    echo "ASR_ALL_DONE $(date)" | tee -a "$LOG"
    say "Tazkiyeh ASR complete" 2>/dev/null || true
    break
  fi
  # one pass over missing with 2 jobs
  bash scripts/run_tazkiyeh_asr_parallel.sh 1 141 "$JOBS" >>"$LOG" 2>&1 || true
  round=$((round+1))
  if [ "$round" -ge 40 ]; then
    echo "ASR_GAVE_UP missing=$(missing_count) $(date)" | tee -a "$LOG"
    break
  fi
  sleep 30
done
