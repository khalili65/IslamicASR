#!/usr/bin/env bash
# Book + summary for Tazkiyeh via ChatGPT browser. Safe to re-run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

START="${1:-1}"
END="${2:-141}"
COURSE="Audios/AyatollahShojaee/Tazkiyeh"
LOG="$COURSE/pipeline_${START}_${END}.log"

echo "=== book pass ${START}-${END} $(date) ===" | tee -a "$LOG"
python scripts/chatgpt_book_style.py "$COURSE" \
  --start "$START" --end "$END" \
  --rate-limit-wait 1800 \
  --delay 8 \
  2>&1 | tee -a "$LOG"

echo "=== summarize pass ${START}-${END} $(date) ===" | tee -a "$LOG"
python scripts/chatgpt_book_style.py "$COURSE" \
  --summarize \
  --start "$START" --end "$END" \
  --rate-limit-wait 1800 \
  --delay 8 \
  2>&1 | tee -a "$LOG"

echo "=== ALL DONE pipeline ${START}-${END} $(date) ===" | tee -a "$LOG"
say "Tazkiyeh pipeline ${START} to ${END} finished" 2>/dev/null || true
