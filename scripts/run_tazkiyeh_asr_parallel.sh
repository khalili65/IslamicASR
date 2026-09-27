#!/usr/bin/env bash
# Parallel ElevenLabs ASR for Tazkiyeh. Safe to re-run (skips existing .txt).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

COURSE="Audios/AyatollahShojaee/Tazkiyeh"
START="${1:-3}"
END="${2:-141}"
JOBS="${3:-4}"
LOG="$COURSE/asr_parallel_${START}_${END}.log"

echo "=== PARALLEL ASR ${START}-${END} jobs=${JOBS} $(date) ===" | tee -a "$LOG"

work_one() {
  local n="$1"
  local d dir mp3 txt
  d=$(printf "%03d" "$n")
  dir="$COURSE/$d"
  if [ ! -d "$dir" ]; then
    echo "[skip] missing $d" | tee -a "$LOG"
    return 0
  fi
  mp3=$(ls "$dir"/*.mp3 2>/dev/null | head -1 || true)
  if [ -z "${mp3:-}" ]; then
    echo "[skip] no mp3 $d" | tee -a "$LOG"
    return 0
  fi
  txt="${mp3%.mp3}.txt"
  if [ -s "$txt" ]; then
    echo "[skip] have txt $d" | tee -a "$LOG"
    python scripts/txt_to_srt.py "$txt" >>"$LOG" 2>&1 || true
    return 0
  fi
  local slog="$dir/transcribe.log"
  echo "[start] $d $(date)" | tee -a "$LOG"
  if python transcribe.py "$mp3" --provider elevenlabs --language fa >"$slog" 2>&1; then
    echo "[ok] $d $(date)" | tee -a "$LOG"
    python scripts/txt_to_srt.py "$txt" >>"$LOG" 2>&1 || true
    # append brief cost line if present
    tail -5 "$slog" >>"$LOG" || true
  else
    echo "[FAIL] $d $(date)" | tee -a "$LOG"
    tail -20 "$slog" >>"$LOG" || true
    return 1
  fi
}

export -f work_one
export COURSE LOG ROOT
# bash work_one needs venv in subshell
export PATH="$ROOT/.venv/bin:$PATH"

seq "$START" "$END" | xargs -P "$JOBS" -n 1 bash -c 'source "'"$ROOT"'/.venv/bin/activate"; work_one "$1"' _

echo "=== PARALLEL DONE ${START}-${END} $(date) ===" | tee -a "$LOG"
say "Tazkiyeh parallel ASR ${START} to ${END} finished" 2>/dev/null || true
