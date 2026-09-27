#!/usr/bin/env bash
# Watchdog: keep Bayat pipeline 11-75 running until book+summary are complete.
# Checks every 20 minutes; restarts if the worker died mid-run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COURSE="$ROOT/Audios/Bayat/marefat_nafs"
LOG="$COURSE/pipeline_11_75.log"
WATCH_LOG="$COURSE/pipeline_watchdog.log"
INTERVAL_SEC=1200  # 20 minutes

count_done() {
  local kind="$1"  # book.md or summary.md
  local n=0
  local d
  for d in $(seq -f "%03g" 11 75); do
    if ls "$COURSE/$d/"*."$kind" >/dev/null 2>&1; then
      n=$((n + 1))
    fi
  done
  echo "$n"
}

pipeline_running() {
  # Match only the real Python worker (avoid matching this watchdog / tick shells).
  pgrep -f "[P]ython scripts/chatgpt_book_style.py Audios/Bayat/marefat_nafs" >/dev/null 2>&1
}

start_pipeline() {
  echo "[$(date)] starting/resuming pipeline batch 11-75" | tee -a "$WATCH_LOG"
  # Run in this same Terminal session (foreground of a background subshell)
  (
    cd "$ROOT"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    bash scripts/run_bayat_pipeline_batch.sh 11 75
  ) &
  echo "[$(date)] worker pid $!" | tee -a "$WATCH_LOG"
}

echo "[$(date)] watchdog started (interval ${INTERVAL_SEC}s)" | tee -a "$WATCH_LOG"

if ! pipeline_running; then
  start_pipeline
fi

while true; do
  books=$(count_done "book.md")
  sums=$(count_done "summary.md")
  echo "[$(date)] status: book=${books}/65 summary=${sums}/65" | tee -a "$WATCH_LOG"

  if [ "$books" -eq 65 ] && [ "$sums" -eq 65 ]; then
    echo "[$(date)] COMPLETE — all book+summary present" | tee -a "$WATCH_LOG"
    say "Bayat pipeline eleven to seventy five finished" || true
    # Final website rebuild if batch script didn't reach it
    cd "$ROOT"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    python3 website/tools/build_content.py --course "$COURSE" --skip-subtitles \
      2>&1 | tee -a "$LOG" || true
    exit 0
  fi

  if ! pipeline_running; then
    echo "[$(date)] worker not running — restarting" | tee -a "$WATCH_LOG"
    start_pipeline
  else
    echo "[$(date)] worker still running" | tee -a "$WATCH_LOG"
  fi

  sleep "$INTERVAL_SEC"
done
