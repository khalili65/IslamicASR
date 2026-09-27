#!/usr/bin/env bash
# Keep Tazkiyeh ASR (003-141) and ChatGPT book+summary progressing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COURSE="$ROOT/Audios/AyatollahShojaee/Tazkiyeh"
WATCH_LOG="$COURSE/pipeline_watchdog.log"
INTERVAL_SEC=900  # 15 min

asr_running() {
  pgrep -f "[b]ash scripts/run_tazkiyeh_asr_batch.sh" >/dev/null 2>&1
}
book_running() {
  pgrep -f "[P]ython scripts/chatgpt_book_style.py Audios/AyatollahShojaee/Tazkiyeh" >/dev/null 2>&1
}

count_txt() { find "$COURSE" -maxdepth 2 -name '*.txt' ! -path '*/.asr_cache*' ! -name '*.partial.txt' | wc -l | tr -d ' '; }
count_book() { find "$COURSE" -maxdepth 2 -name '*.book.md' | wc -l | tr -d ' '; }
count_sum() { find "$COURSE" -maxdepth 2 -name '*.summary.md' | wc -l | tr -d ' '; }

start_asr() {
  echo "[$(date)] starting ASR 3-141" | tee -a "$WATCH_LOG"
  (
    cd "$ROOT"
    source .venv/bin/activate
    bash scripts/run_tazkiyeh_asr_batch.sh 3 141
  ) >>"$COURSE/asr_003_141.nohup.out" 2>&1 &
  echo "[$(date)] ASR pid $!" | tee -a "$WATCH_LOG"
}

start_book() {
  echo "[$(date)] starting/resuming book+summary 1-141" | tee -a "$WATCH_LOG"
  (
    cd "$ROOT"
    source .venv/bin/activate
    bash scripts/run_tazkiyeh_pipeline_batch.sh 1 141
  ) >>"$COURSE/pipeline_1_141.nohup.out" 2>&1 &
  echo "[$(date)] book pid $!" | tee -a "$WATCH_LOG"
}

echo "[$(date)] tazkiyeh watchdog started" | tee -a "$WATCH_LOG"
while true; do
  txt=$(count_txt); book=$(count_book); sum=$(count_sum)
  echo "[$(date)] status txt=$txt book=$book summary=$sum" | tee -a "$WATCH_LOG"
  if ! asr_running; then
    # restart only if not all txt present
    if [ "$txt" -lt 141 ]; then
      start_asr
    fi
  fi
  if ! book_running; then
    if [ "$txt" -gt "$book" ] || [ "$book" -gt "$sum" ]; then
      start_book
    fi
  fi
  if [ "$txt" -ge 141 ] && [ "$book" -ge 141 ] && [ "$sum" -ge 141 ]; then
    echo "[$(date)] ALL COMPLETE" | tee -a "$WATCH_LOG"
    say "Tazkiyeh pipeline complete" 2>/dev/null || true
    break
  fi
  sleep "$INTERVAL_SEC"
done
