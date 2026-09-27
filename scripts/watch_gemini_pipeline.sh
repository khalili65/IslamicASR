#!/usr/bin/env bash
# Health loop for the Gemini book/summary pipeline.
#
# Every INTERVAL seconds: report progress, and if no new part_*.md has been
# written for STALL_AFTER seconds, kill the run and resume it from cache.
# Gemini's UI freezes now and then; resuming is cheap because finished chunks
# are cached on disk.

set -uo pipefail

REPO="/Users/mohammadreza/IslamASR"
TARGET="Audios/Qasemian/InsaneKamel"
LOG="/tmp/logs/flash_book.log"
WATCHLOG="/tmp/logs/watchdog.log"
INTERVAL="${INTERVAL:-300}"
STALL_AFTER="${STALL_AFTER:-600}"
JOBS="${JOBS:-1}"

cd "$REPO" || exit 1
mkdir -p /tmp/logs

say() { echo "[$(date '+%H:%M:%S')] $*" >> "$WATCHLOG"; }

part_count() { find "$TARGET" -name 'part_*.md' 2>/dev/null | wc -l | tr -d ' '; }
book_count() { find "$TARGET" -name '*.book.md' -not -path '*_legacy*' 2>/dev/null | wc -l | tr -d ' '; }

summary_count() {
  find "$TARGET" -name '*.summary.md' -not -path '*_legacy*' 2>/dev/null | wc -l | tr -d ' '
}

start_run() {
  # shellcheck disable=SC1091
  source .venv/bin/activate
  local phase=()
  # Books first; once all 63 exist, the same loop drives the summary pass.
  if [ "$(book_count)" -ge 63 ]; then
    phase=(--summarize)
    say "book step complete — running summary pass"
  fi
  nohup python scripts/gemini_book_style.py "$TARGET" "${phase[@]}" \
    --model "3.7 Flash" --allow-flash --jobs "$JOBS" \
    --settle 8 --response-timeout 300 >> "$LOG" 2>&1 &
  say "started pipeline (pid $!, jobs=$JOBS) ${phase[*]}"
}

last_change=$(date +%s)
last_parts=$(part_count)

while true; do
  sleep "$INTERVAL"

  parts=$(part_count)
  books=$(book_count)
  now=$(date +%s)

  if [ "$parts" != "$last_parts" ]; then
    last_change=$now
    last_parts=$parts
  fi
  idle=$(( now - last_change ))

  if pgrep -f "gemini_book_style.py $TARGET" >/dev/null; then
    say "alive | parts=$parts books=$books/63 | idle=${idle}s"
    if [ "$idle" -ge "$STALL_AFTER" ]; then
      say "STALLED ${idle}s with no new part — restarting"
      pkill -f "gemini_book_style.py $TARGET"
      sleep 5
      start_run
      last_change=$(date +%s)
    fi
  else
    sums=$(summary_count)
    if [ "$books" -ge 63 ] && [ "$sums" -ge 63 ]; then
      say "all 63 books and 63 summaries done — watchdog exiting"
      exit 0
    fi
    say "process gone | parts=$parts books=$books/63 summaries=$sums/63 — resuming"
    start_run
    last_change=$(date +%s)
  fi
done
