#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
COURSE="Audios/AyatollahShojaee/Mabahese_Tohidi"
LOG="$COURSE/asr.log"
N=16
JOBS=2

missing_list() {
  local d
  for d in $(seq -f '%03g' 1 "$N"); do
    if ! find "$COURSE/$d" -maxdepth 1 -name '*.txt' ! -name '*partial*' -size +1k 2>/dev/null | grep -q .; then
      echo "$d"
    fi
  done
}

work_one() {
  local d="$1"
  local dir="$COURSE/$d"
  local mp3 txt
  mp3=$(ls "$dir"/*.mp3 2>/dev/null | head -1 || true)
  if [ -z "${mp3:-}" ]; then
    echo "[no-mp3] $d" | tee -a "$LOG"
    return 0
  fi
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

: > "$LOG"
echo "ASR begin $(date) N=$N jobs=$JOBS" | tee -a "$LOG"
round=0
while true; do
  mapfile -t miss < <(missing_list)
  echo "[$(date)] missing=${#miss[@]} round=$round" | tee -a "$LOG"
  if [ "${#miss[@]}" -eq 0 ]; then
    echo "ASR_ALL_DONE $(date)" | tee -a "$LOG"
    break
  fi
  printf '%s\n' "${miss[@]}" | xargs -P "$JOBS" -n 1 -I{} bash -c 'source "'"$ROOT"'/.venv/bin/activate"; work_one "$@"' _ {}
  round=$((round+1))
  if [ "$round" -ge 40 ]; then
    echo "ASR_GAVE_UP $(date)" | tee -a "$LOG"
    break
  fi
  sleep 15
done
echo "ASR_SCRIPT_DONE $(date)" | tee -a "$LOG"
