#!/usr/bin/env bash
# Transcribe Tazkiyeh sessions with ElevenLabs. Safe to re-run (skips existing .txt).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate

COURSE="Audios/AyatollahShojaee/Tazkiyeh"
START="${1:-3}"
END="${2:-141}"
LOG="$COURSE/asr_${START}_${END}.log"

echo "=== ASR ${START}-${END} $(date) ===" | tee -a "$LOG"

for n in $(seq "$START" "$END"); do
  d=$(printf "%03d" "$n")
  dir="$COURSE/$d"
  if [ ! -d "$dir" ]; then
    echo "[skip] missing dir $d" | tee -a "$LOG"
    continue
  fi
  mp3=$(ls "$dir"/*.mp3 2>/dev/null | head -1 || true)
  if [ -z "${mp3:-}" ]; then
    echo "[skip] no mp3 in $d" | tee -a "$LOG"
    continue
  fi
  txt="${mp3%.mp3}.txt"
  if [ -s "$txt" ]; then
    echo "[skip] already have txt $d" | tee -a "$LOG"
    # still ensure srt
    python scripts/txt_to_srt.py "$txt" 2>&1 | tee -a "$LOG" || true
    continue
  fi
  echo "=== transcribe $d $(date) ===" | tee -a "$LOG"
  if python transcribe.py "$mp3" --provider elevenlabs --language fa 2>&1 | tee -a "$LOG"; then
    echo "[ok] $d" | tee -a "$LOG"
    python scripts/txt_to_srt.py "$txt" 2>&1 | tee -a "$LOG" || true
  else
    echo "[FAIL] $d" | tee -a "$LOG"
  fi
done

echo "=== ASR DONE ${START}-${END} $(date) ===" | tee -a "$LOG"
say "Tazkiyeh ASR ${START} to ${END} finished" 2>/dev/null || true
