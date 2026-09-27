#!/bin/bash
set -euo pipefail
cd /Users/mohammadreza/IslamASR
export ISLAMASR_ROOT="$PWD"
export TERM5_SKIP_ASR=1
export ISLAMASR_VENV_PY="${ISLAMASR_VENV_PY:-$PWD/.venv/bin/python}"
[[ -f "$PWD/website/tools/prepare_playback.py" ]] && export ISLAMASR_PREPARE_PLAYBACK="$PWD/website/tools/prepare_playback.py"
echo "Downloading+remuxing Term5 audio (ASR skipped)…"
"$ISLAMASR_VENV_PY" scripts/download_sobohi_term5.py
echo Done.
