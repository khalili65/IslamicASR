#!/usr/bin/env bash
# Run new pipeline (book + summary) for Bayat marefat_nafs sessions.
# Safe to re-run: skips sessions that already have outputs; resumes from .book_parts_ caches.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate

START="${1:-11}"
END="${2:-75}"
COURSE="Audios/Bayat/marefat_nafs"
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

echo "=== rebuild website $(date) ===" | tee -a "$LOG"
python3 website/tools/build_content.py --course "$ROOT/$COURSE" --skip-subtitles \
  2>&1 | tee -a "$LOG"

echo "=== ALL DONE ${START}-${END} $(date) ===" | tee -a "$LOG"
say "Bayat pipeline ${START} to ${END} finished" || true
