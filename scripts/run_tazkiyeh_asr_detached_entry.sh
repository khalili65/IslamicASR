#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate
LOG="$ROOT/Audios/AyatollahShojaee/Tazkiyeh/asr_3_141.log"
echo "[$(date)] detached entry starting" >> "$LOG"
# If a 003 transcribe is already running, wait for it
while pgrep -f "transcribe.py Audios/AyatollahShojaee/Tazkiyeh/003/" >/dev/null 2>&1; do
  echo "[$(date)] waiting for in-flight 003..." >> "$LOG"
  sleep 10
done
# If 003 txt exists, make srt
shopt -s nullglob
for t in Audios/AyatollahShojaee/Tazkiyeh/003/*.txt; do
  [[ "$t" == *.partial.txt ]] && continue
  python scripts/txt_to_srt.py "$t" >>"$LOG" 2>&1 || true
done
shopt -u nullglob
exec bash scripts/run_tazkiyeh_asr_batch.sh 3 141
